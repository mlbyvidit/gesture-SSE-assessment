import os
import uuid
import logging

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.models import ChatRequest, ChatResponse, DecisionData, SessionSummaryResponse
from app.session_store import (
    create_session,
    get_session,
    add_message,
    get_conversation_history,
    set_phase,
    update_profile,
    add_intent_score,
    check_rate_limit,
    delete_session,
    list_sessions,
    update_session,
)
from app.intake_agent import run_intake
from app.recommendation_agent import run_recommendation, run_followup

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gesture Decision Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_HIGH_INTENT_WORDS = [
    "pricing", "price", "cost", "budget", "how much",
    "ready", "start", "contract", "timeline", "pilot",
    "integrate", "asap", "urgent", "next steps", "sign up",
]
_MID_INTENT_WORDS = [
    "interested", "considering", "demo", "example",
    "tell me more", "how does", "what is", "case study",
]


def _compute_intent_score(message: str, message_count: int) -> float:
    lower = message.lower()
    score = 0.0
    if any(w in lower for w in _HIGH_INTENT_WORDS):
        score += 0.25
    if any(w in lower for w in _MID_INTENT_WORDS):
        score += 0.12
    if message_count > 4:
        score += 0.15
    if message_count > 8:
        score += 0.10
    return min(score, 1.0)


def _intent_tier(score: float) -> str:
    if score >= 0.65:
        return "high_intent"
    if score >= 0.35:
        return "engaged"
    return "browsing"


# ─────────────────────────────────────────────────────
# POST /chat
# ─────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()

    if not message:
        raise HTTPException(status_code=422, detail="Message must not be empty.")
    if len(message) > 1000:
        raise HTTPException(status_code=422, detail="Message exceeds 1000 character limit.")

    # Session resolution
    if request.session_id:
        session_id = request.session_id
        session = get_session(session_id)
        if session is None:
            session = create_session(session_id)
    else:
        session_id = str(uuid.uuid4())
        session = create_session(session_id)

    # Rate limit
    if not check_rate_limit(session_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")

    # Record user message
    add_message(session_id, "user", message)

    # Intent scoring
    session = get_session(session_id)
    score = _compute_intent_score(message, len(session.messages))
    add_intent_score(session_id, score)
    tier = _intent_tier(score)

    # ── Intake phase ──────────────────────────────────
    if session.phase == "intake":
        result = await run_intake(message, get_conversation_history(session_id), session_id)

        if result["profile_complete"]:
            update_profile(session_id, result["profile_data"])
            set_phase(session_id, "recommendation")

            recommendation = await run_recommendation(
                result["profile_data"],
                get_conversation_history(session_id),
                session_id,
            )

            combined_message = result["chat_message"] + "\n\n" + recommendation["chat_message"]
            add_message(session_id, "assistant", combined_message)

            decision_raw = recommendation["decision"] or {}
            # Persist decision so Sales Dashboard can read it without re-calling the LLM
            update_session(session_id, {"last_decision_raw": decision_raw})
            decision = DecisionData(
                vertical=decision_raw.get("vertical", "gifting"),
                vertical_description=decision_raw.get("vertical_description", ""),
                recommended_campaign=decision_raw.get("recommended_campaign", ""),
                confidence_score=min(max(float(decision_raw.get("confidence_score", 0.5)), 0.0), 1.0),
                intent_tier=decision_raw.get("intent_tier", tier),
                intent_description=decision_raw.get("intent_description", ""),
                reasoning=decision_raw.get("reasoning", ""),
                next_questions=decision_raw.get("next_questions", []),
            )

            return ChatResponse(
                chat_message=combined_message,
                session_id=session_id,
                phase="recommendation",
                is_complete=True,
                decision=decision,
            )

        add_message(session_id, "assistant", result["chat_message"])
        return ChatResponse(
            chat_message=result["chat_message"],
            session_id=session_id,
            phase="intake",
            is_complete=False,
            decision=None,
        )

    # ── Recommendation / follow-up phase ──────────────
    result = await run_followup(
        message,
        get_conversation_history(session_id),
        get_session(session_id).profile.model_dump(),
        session_id,
    )
    add_message(session_id, "assistant", result["chat_message"])

    return ChatResponse(
        chat_message=result["chat_message"],
        session_id=session_id,
        phase="recommendation",
        is_complete=True,
        decision=None,
    )


# ─────────────────────────────────────────────────────
# GET /session/{session_id}/summary
# ─────────────────────────────────────────────────────

@app.get("/session/{session_id}/summary", response_model=SessionSummaryResponse)
async def session_summary(session_id: str) -> SessionSummaryResponse:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    scores = session.intent_score_history
    final_tier = _intent_tier(scores[-1]) if scores else None

    # CRM summary via Mistral
    crm_summary: str | None = None
    api_key = os.getenv("MISTRAL_API_KEY")
    if api_key:
        import json
        profile_json = json.dumps(session.profile.model_dump(), indent=2)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "mistral-small-latest",
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    "Based on this conversation profile, write ONE sentence for a sales CRM "
                                    "describing this lead. Be specific about their company situation, what they "
                                    f"need, and urgency level.\nProfile: {profile_json}"
                                ),
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 100,
                    },
                )
                resp.raise_for_status()
                crm_summary = resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("session=%s failed to generate CRM summary: %s", session_id, exc)

    return SessionSummaryResponse(
        session_id=session_id,
        total_turns=len(session.messages),
        phase=session.phase,
        profile=session.profile,
        final_intent_tier=final_tier,
        intent_score_progression=scores,
        top_vertical=None,
        crm_summary=crm_summary,
    )


# ─────────────────────────────────────────────────────
# DELETE /session/{session_id}
# ─────────────────────────────────────────────────────

@app.delete("/session/{session_id}")
async def remove_session(session_id: str) -> dict:
    delete_session(session_id)
    return {"deleted": True}


# ─────────────────────────────────────────────────────
# GET /sessions  (Sales Dashboard — all active sessions)
# ─────────────────────────────────────────────────────

@app.get("/sessions")
async def get_all_sessions() -> list[dict]:
    import time as _time
    sessions = list_sessions()
    result = []
    for s in sessions:
        dec = s.last_decision_raw or {}
        scores = s.intent_score_history
        tier = _intent_tier(scores[-1]) if scores else "browsing"
        result.append({
            "session_id": s.session_id,
            "phase": s.phase,
            "turn_count": len(s.messages),
            "last_updated": s.last_updated,
            "seconds_ago": round(_time.time() - s.last_updated),
            "vertical": dec.get("vertical"),
            "intent_tier": dec.get("intent_tier") or tier,
            "confidence_score": dec.get("confidence_score"),
            "profile": s.profile.model_dump(),
        })
    # Most recently active first
    result.sort(key=lambda x: x["last_updated"], reverse=True)
    return result


# ─────────────────────────────────────────────────────
# GET /health
# ─────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}


# ─────────────────────────────────────────────────────
# Static files — mount last so API routes take priority
# ─────────────────────────────────────────────────────

if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
