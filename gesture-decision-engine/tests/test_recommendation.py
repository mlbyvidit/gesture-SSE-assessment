import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


_SAMPLE_PROFILE = {
    "audience": "customers",
    "scale": "large",
    "goal": "retention",
    "timeline": "immediate",
    "existing_program": True,
    "pain_point": "redemption rates are only 15%",
    "company_type": "retail",
    "raw_quotes": ["redemption rates are only 15%"],
    "is_complete": True,
}

_VALID_DECISION = {
    "vertical": "loyalty",
    "vertical_description": "Tangible rewards that make loyalty programs feel real.",
    "recommended_campaign": "Points-to-Gift — let members redeem points for curated physical gifts",
    "confidence_score": 0.87,
    "intent_tier": "high_intent",
    "intent_description": "Prospect has clear pain, budget signal, and wants to move in Q1.",
    "reasoning": "The prospect has 50,000 loyalty members with low redemption. Points-to-Gift directly solves this.",
    "next_questions": [
        "What platform manages your loyalty points today?",
        "Do you have a preferred gift budget per member?",
        "Would a 90-day pilot work for your Q1 timeline?",
    ],
}


def _make_mistral_response(content: str) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    return mock_resp


# ── build_recommendation_prompt ─────────────────────

def test_build_recommendation_prompt_includes_profile():
    from app.recommendation_agent import build_recommendation_prompt

    prompt = build_recommendation_prompt(_SAMPLE_PROFILE, "PRODUCT_KNOWLEDGE_STUB")
    assert "customers" in prompt
    assert "retention" in prompt
    assert "redemption rates are only 15%" in prompt


def test_build_recommendation_prompt_includes_product_knowledge():
    from app.recommendation_agent import build_recommendation_prompt

    knowledge = "UNIQUE_KNOWLEDGE_SENTINEL_XYZ"
    prompt = build_recommendation_prompt(_SAMPLE_PROFILE, knowledge)
    assert knowledge in prompt


def test_build_recommendation_prompt_includes_decision_sentinel():
    from app.recommendation_agent import build_recommendation_prompt

    prompt = build_recommendation_prompt(_SAMPLE_PROFILE, "knowledge")
    assert "---DECISION---" in prompt


# ── run_recommendation ───────────────────────────────

@pytest.mark.asyncio
async def test_decision_parsed_correctly_from_response():
    from app.recommendation_agent import run_recommendation

    chat_part = "Based on what you've told me, here is my recommendation for your loyalty program."
    reply = f"{chat_part}\n---DECISION---\n{json.dumps(_VALID_DECISION)}"
    mock_resp = _make_mistral_response(reply)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await run_recommendation(_SAMPLE_PROFILE, [], "sess-r-001")

    assert result["chat_message"] == chat_part
    assert result["decision"] is not None
    assert result["decision"]["vertical"] == "loyalty"
    assert result["decision"]["confidence_score"] == pytest.approx(0.87)
    assert result["decision"]["intent_tier"] == "high_intent"
    assert len(result["decision"]["next_questions"]) == 3


@pytest.mark.asyncio
async def test_fallback_used_when_decision_json_is_malformed():
    from app.recommendation_agent import run_recommendation, _FALLBACK_DECISION

    chat_part = "Here is what I recommend for you."
    reply = f"{chat_part}\n---DECISION---\n{{ not valid json !!!"
    mock_resp = _make_mistral_response(reply)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await run_recommendation(_SAMPLE_PROFILE, [], "sess-r-002")

    assert result["chat_message"] == chat_part
    assert result["decision"] == _FALLBACK_DECISION


@pytest.mark.asyncio
async def test_fallback_used_when_sentinel_missing():
    from app.recommendation_agent import run_recommendation, _FALLBACK_DECISION

    reply = "Here is my recommendation but I forgot the sentinel."
    mock_resp = _make_mistral_response(reply)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await run_recommendation(_SAMPLE_PROFILE, [], "sess-r-003")

    assert result["chat_message"] == reply
    assert result["decision"] == _FALLBACK_DECISION


@pytest.mark.asyncio
async def test_missing_fields_patched_from_fallback():
    from app.recommendation_agent import run_recommendation, _FALLBACK_DECISION

    # Decision JSON is valid but missing several required fields
    partial_decision = {
        "vertical": "loyalty",
        "confidence_score": 0.75,
    }
    chat_part = "Here is your recommendation."
    reply = f"{chat_part}\n---DECISION---\n{json.dumps(partial_decision)}"
    mock_resp = _make_mistral_response(reply)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await run_recommendation(_SAMPLE_PROFILE, [], "sess-r-004")

    d = result["decision"]
    assert d is not None
    assert d["vertical"] == "loyalty"           # preserved from LLM
    assert d["confidence_score"] == 0.75         # preserved from LLM
    # Missing fields filled from fallback
    assert d["reasoning"] == _FALLBACK_DECISION["reasoning"]
    assert d["next_questions"] == _FALLBACK_DECISION["next_questions"]


# ── run_followup ─────────────────────────────────────

@pytest.mark.asyncio
async def test_followup_returns_chat_message_only():
    from app.recommendation_agent import run_followup

    reply = "Great question — our pilot starts at 100 gifts with no long-term commitment."
    mock_resp = _make_mistral_response(reply)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await run_followup("What does the pilot look like?", [], _SAMPLE_PROFILE, "sess-r-005")

    assert result["chat_message"] == reply
    assert "decision" not in result
