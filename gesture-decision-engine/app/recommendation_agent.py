import json
import os
import logging

import httpx

from app.product_knowledge import get_knowledge_as_string

logger = logging.getLogger(__name__)

_MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

_REQUIRED_DECISION_FIELDS = {
    "vertical",
    "vertical_description",
    "recommended_campaign",
    "confidence_score",
    "intent_tier",
    "intent_description",
    "reasoning",
    "next_questions",
}

_FALLBACK_DECISION = {
    "vertical": "gifting",
    "vertical_description": "Unable to parse structured decision — defaulting to gifting vertical.",
    "recommended_campaign": "Gift Finder — AI-powered quiz that matches a gift to the recipient's profile",
    "confidence_score": 0.5,
    "intent_tier": "engaged",
    "intent_description": "Prospect completed intake but decision data could not be parsed.",
    "reasoning": "Fallback decision used due to a JSON parsing error. Profile was collected successfully.",
    "next_questions": [
        "What does your current customer engagement program look like?",
        "How many recipients would you expect in your first campaign?",
        "Would a 90-day pilot with no long-term commitment work for your timeline?",
    ],
}


def build_recommendation_prompt(profile: dict, product_knowledge: str) -> str:
    return f"""You are Maya, a senior Gesture product expert.

A prospect has just completed an intake conversation and here is everything we know about them:

PROSPECT PROFILE:
{json.dumps(profile, indent=2)}

YOUR PRODUCT KNOWLEDGE BASE — everything you know about Gesture:
{product_knowledge}

YOUR JOB NOW:
Give this prospect a detailed, specific, genuinely helpful recommendation based on their exact situation. This is where you switch from collecting information to being a true product expert.

RESPONSE RULES:
- Address their specific situation directly — reference their scale, their goal, their pain point using their own words where possible
- Recommend the most relevant Gesture vertical and specific products by name
- Include real pricing from the knowledge base — be specific, not vague
- Give realistic timelines for their situation
- Include a specific metric or result that is relevant to their goal
- Handle any objections they might have based on what they told you
- End with ONE specific question that moves them toward next steps
- Be warm and direct — like a trusted advisor, not a brochure
- Length: 4 to 6 sentences in the main recommendation, then the closing question

IMPORTANT: You are still Maya — same warm personality, now going deeper.
The user should feel like the same person who collected their info is now giving them expert advice.

After your conversational recommendation, on a new line write exactly:
---DECISION---
Then on the VERY NEXT LINE write raw JSON only (NO markdown fences, NO ```json, NO backticks — just the raw {{ }} object):
{{
  "vertical": "one of: gifting, loyalty, brand_engagement, enterprise_rewards",
  "vertical_description": "one sentence description of why this vertical fits",
  "recommended_campaign": "specific product name — one line description of what it does",
  "confidence_score": float between 0.0 and 1.0,
  "intent_tier": "browsing or engaged or high_intent",
  "intent_description": "one sentence about where this prospect is in the buying journey",
  "reasoning": "2 sentences referencing specific signals from their profile",
  "next_questions": ["question 1", "question 2", "question 3"]
}}
"""


async def _extract_decision_json(
    chat_reply: str,
    profile: dict,
    api_key: str,
    session_id: str,
) -> dict:
    """Second micro-call: extract structured decision JSON from the chat reply."""
    profile_summary = json.dumps(
        {k: profile.get(k) for k in ("audience", "scale", "goal", "timeline", "pain_point")},
        indent=2,
    )
    extraction_prompt = (
        "You are a data extraction assistant. Given the recommendation below and the prospect "
        "profile, output ONLY a single raw JSON object with no surrounding text, no markdown "
        "fences, no explanation.\n\n"
        f"PROSPECT PROFILE:\n{profile_summary}\n\n"
        f"RECOMMENDATION TEXT:\n{chat_reply}\n\n"
        "Output a JSON object with exactly these fields:\n"
        '{\n'
        '  "vertical": "one of: gifting, loyalty, brand_engagement, enterprise_rewards",\n'
        '  "vertical_description": "one sentence why this vertical fits",\n'
        '  "recommended_campaign": "specific product name and one-line description",\n'
        '  "confidence_score": 0.0 to 1.0 float,\n'
        '  "intent_tier": "browsing or engaged or high_intent",\n'
        '  "intent_description": "one sentence about buying journey",\n'
        '  "reasoning": "two sentences referencing profile signals",\n'
        '  "next_questions": ["question 1", "question 2", "question 3"]\n'
        "}\n\n"
        "Output ONLY the JSON object. Nothing else."
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                _MISTRAL_API_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "mistral-small-latest",
                    "messages": [{"role": "user", "content": extraction_prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip any markdown fences just in case
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            raw = raw.rsplit("```", 1)[0].strip()

        decision = json.loads(raw)
        missing = _REQUIRED_DECISION_FIELDS - decision.keys()
        for field in missing:
            decision[field] = _FALLBACK_DECISION[field]
        return decision

    except Exception as exc:
        logger.error("session=%s decision extraction failed: %s", session_id, exc)
        return _FALLBACK_DECISION


async def run_recommendation(
    profile: dict,
    conversation_history: list[dict],
    session_id: str,
) -> dict:
    api_key = os.getenv("MISTRAL_API_KEY")
    product_knowledge = get_knowledge_as_string()
    system_prompt = build_recommendation_prompt(profile, product_knowledge)

    recent_history = conversation_history[-6:]

    messages = (
        [{"role": "system", "content": system_prompt}]
        + recent_history
        + [
            {
                "role": "user",
                "content": "Based on everything I have shared, what would you specifically recommend for us?",
            }
        ]
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _MISTRAL_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "mistral-small-latest",
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 1000,
                },
            )
            response.raise_for_status()
            data = response.json()

        reply: str = data["choices"][0]["message"]["content"]

        # Try to parse inline sentinel first (in case model does include it)
        chat_part = reply.strip()
        if "---DECISION---" in reply:
            parts = reply.split("---DECISION---", 1)
            chat_part = parts[0].strip()  # preserve the clean chat text either way
            json_part = parts[1].strip()
            if json_part.startswith("```"):
                json_part = json_part.split("\n", 1)[-1]
                json_part = json_part.rsplit("```", 1)[0].strip()
            try:
                decision_data = json.loads(json_part)
                missing = _REQUIRED_DECISION_FIELDS - decision_data.keys()
                for field in missing:
                    decision_data[field] = _FALLBACK_DECISION[field]
                return {"chat_message": chat_part, "decision": decision_data}
            except json.JSONDecodeError:
                pass  # fall through to extraction call

        # Sentinel missing or JSON malformed — extract via dedicated second call
        logger.info("session=%s using extraction call for decision JSON", session_id)
        decision_data = await _extract_decision_json(chat_part, profile, api_key or "", session_id)

        return {"chat_message": chat_part, "decision": decision_data}

    except httpx.TimeoutException:
        logger.warning("session=%s recommendation API call timed out", session_id)
        return {
            "chat_message": (
                "Sorry, it's taking a moment to pull your recommendation together. "
                "Please try again and I'll have it ready right away."
            ),
            "decision": None,
        }

    except Exception as exc:
        logger.exception(
            "session=%s unexpected error in run_recommendation: %s", session_id, exc
        )
        return {
            "chat_message": (
                "Apologies — something went wrong while preparing your recommendation. "
                "Please try again in a moment."
            ),
            "decision": None,
        }


async def run_followup(
    user_message: str,
    conversation_history: list[dict],
    profile: dict,
    session_id: str,
) -> dict:
    api_key = os.getenv("MISTRAL_API_KEY")
    product_knowledge = get_knowledge_as_string()
    profile_json = json.dumps(profile, indent=2)

    system_prompt = (
        f"You are Maya, a Gesture product expert. You have already given this prospect a recommendation. "
        f"Here is their profile for context:\n{profile_json}\n\n"
        f"Here is your product knowledge:\n{product_knowledge}\n\n"
        f"Answer their follow-up question specifically and helpfully. "
        f"Reference real pricing, timelines, and product details from your knowledge base. "
        f"Keep it conversational — 3 to 4 sentences. "
        f"Do not repeat the full recommendation unless asked."
    )

    recent_history = conversation_history[-6:]

    messages = (
        [{"role": "system", "content": system_prompt}]
        + recent_history
        + [{"role": "user", "content": user_message}]
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _MISTRAL_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "mistral-small-latest",
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 400,
                },
            )
            response.raise_for_status()
            data = response.json()

        reply: str = data["choices"][0]["message"]["content"]
        return {"chat_message": reply}

    except httpx.TimeoutException:
        logger.warning("session=%s followup API call timed out", session_id)
        return {
            "chat_message": (
                "That took a little longer than expected — could you ask again "
                "and I'll get you an answer straight away?"
            )
        }

    except Exception as exc:
        logger.exception(
            "session=%s unexpected error in run_followup: %s", session_id, exc
        )
        return {
            "chat_message": (
                "Apologies — something went wrong on my end. "
                "Please try your question again."
            )
        }
