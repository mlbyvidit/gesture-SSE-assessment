"""
End-to-end tests against the running FastAPI server.
Skipped automatically when the server is not reachable on localhost:8000.
Run with: pytest tests/test_e2e.py -v  (server must be running)
"""
import pytest
import httpx

BASE = "http://localhost:8000"
TIMEOUT = 60.0  # LLM calls can be slow

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


def _server_running() -> bool:
    try:
        httpx.get(f"{BASE}/health", timeout=3.0)
        return True
    except Exception:
        return False


skip_if_offline = pytest.mark.skipif(
    not _server_running(),
    reason="Server not running on localhost:8000 — skipping e2e tests",
)


# ── Health ───────────────────────────────────────────

@skip_if_offline
def test_health_endpoint():
    resp = httpx.get(f"{BASE}/health", timeout=5.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ── Full loyalty conversation flow ───────────────────

TURNS = [
    "hi",
    "we are a retail brand with 50000 loyalty members",
    "our redemption rates are terrible, we want to fix this fast",
    "we want to launch in Q1",
]


@skip_if_offline
def test_full_loyalty_conversation():
    session_id: str | None = None

    for i, message in enumerate(TURNS):
        payload: dict = {"message": message}
        if session_id:
            payload["session_id"] = session_id

        resp = httpx.post(f"{BASE}/chat", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Turn {i+1} failed: {resp.text}"

        data = resp.json()

        # Every turn must have these fields
        assert "chat_message" in data, f"Turn {i+1} missing chat_message"
        assert "session_id" in data,   f"Turn {i+1} missing session_id"
        assert "phase" in data,        f"Turn {i+1} missing phase"
        assert isinstance(data["chat_message"], str)
        assert len(data["chat_message"]) > 0

        # Session id must be stable once set
        if session_id is None:
            session_id = data["session_id"]
        else:
            assert data["session_id"] == session_id, "session_id changed mid-conversation"

    # After the final turn, the recommendation should be complete
    assert data["phase"] == "recommendation", \
        f"Expected recommendation phase after 4 turns, got: {data['phase']}"
    assert data["is_complete"] is True

    # Decision must be present and fully formed
    decision = data.get("decision")
    assert decision is not None, "Decision is missing after recommendation phase"
    missing = _REQUIRED_DECISION_FIELDS - decision.keys()
    assert not missing, f"Decision missing fields: {missing}"

    # Field-level sanity checks
    assert decision["vertical"] in {"gifting", "loyalty", "brand_engagement", "enterprise_rewards"}
    assert 0.0 <= decision["confidence_score"] <= 1.0
    assert decision["intent_tier"] in {"browsing", "engaged", "high_intent"}
    assert isinstance(decision["next_questions"], list)
    assert len(decision["next_questions"]) > 0
    assert isinstance(decision["reasoning"], str) and len(decision["reasoning"]) > 0

    return session_id  # used by summary test below


@skip_if_offline
def test_session_summary_after_conversation():
    # Run the conversation first to get a session_id
    session_id: str | None = None

    for message in TURNS:
        payload: dict = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        resp = httpx.post(f"{BASE}/chat", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

    assert session_id is not None

    # Now fetch the summary
    resp = httpx.get(f"{BASE}/session/{session_id}/summary", timeout=TIMEOUT)
    assert resp.status_code == 200

    summary = resp.json()
    assert summary["session_id"] == session_id
    assert summary["total_turns"] == len(TURNS) * 2  # user + assistant per turn
    assert summary["phase"] == "recommendation"
    assert "profile" in summary
    assert "intent_score_progression" in summary
    assert isinstance(summary["intent_score_progression"], list)


@skip_if_offline
def test_rate_limit_returns_429_after_30_rapid_requests():
    # Use a fresh session that will never have 30 prior requests
    # Fire 31 requests quickly — the 31st should be rate-limited
    session_id = "rate-limit-test-session-" + str(__import__("time").time_ns())

    statuses: list[int] = []
    for i in range(31):
        resp = httpx.post(
            f"{BASE}/chat",
            json={"message": f"message {i}", "session_id": session_id},
            timeout=10.0,
        )
        statuses.append(resp.status_code)

    assert 429 in statuses, f"Expected a 429 somewhere in {statuses}"


@skip_if_offline
def test_missing_session_returns_404():
    resp = httpx.get(f"{BASE}/session/nonexistent-session-xyz/summary", timeout=5.0)
    assert resp.status_code == 404


@skip_if_offline
def test_delete_session():
    # Create a session
    resp = httpx.post(f"{BASE}/chat", json={"message": "hi"}, timeout=TIMEOUT)
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Delete it
    resp = httpx.delete(f"{BASE}/session/{session_id}", timeout=5.0)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Summary should now 404
    resp = httpx.get(f"{BASE}/session/{session_id}/summary", timeout=5.0)
    assert resp.status_code == 404
