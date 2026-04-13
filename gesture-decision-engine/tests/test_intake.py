import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock


def _make_mistral_response(content: str) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    return mock_resp


@pytest.mark.asyncio
async def test_profile_not_complete_returns_chat_message():
    from app.intake_agent import run_intake

    reply = "Hi! Great to meet you. What type of audience are you trying to reach?"
    mock_resp = _make_mistral_response(reply)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await run_intake("hi", [], "sess-001")

    assert result["profile_complete"] is False
    assert result["chat_message"] == reply
    assert result["profile_data"] is None


@pytest.mark.asyncio
async def test_profile_complete_detected_and_parsed():
    from app.intake_agent import run_intake

    profile_payload = {
        "audience": "customers",
        "scale": "large",
        "goal": "retention",
        "timeline": "immediate",
        "existing_program": True,
        "pain_point": "churn is rising every quarter",
        "company_type": "retail",
        "raw_quotes": ["churn is rising every quarter"],
    }
    chat_part = "Great, I have everything I need — pulling your recommendation now."
    reply = f"{chat_part}\nPROFILE_COMPLETE\n{json.dumps(profile_payload)}"
    mock_resp = _make_mistral_response(reply)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await run_intake("we want to improve retention urgently", [], "sess-002")

    assert result["profile_complete"] is True
    assert result["chat_message"] == chat_part
    assert result["profile_data"] is not None
    assert result["profile_data"]["audience"] == "customers"
    assert result["profile_data"]["scale"] == "large"
    assert result["profile_data"]["goal"] == "retention"
    assert result["profile_data"]["timeline"] == "immediate"
    assert result["profile_data"]["existing_program"] is True


@pytest.mark.asyncio
async def test_malformed_json_after_profile_complete_returns_recovery_message():
    from app.intake_agent import run_intake

    reply = "Perfect, I have what I need.\nPROFILE_COMPLETE\n{ this is not valid json !!!"
    mock_resp = _make_mistral_response(reply)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await run_intake("I want to start immediately", [], "sess-003")

    assert result["profile_complete"] is False
    assert result["profile_data"] is None
    assert isinstance(result["chat_message"], str)
    assert len(result["chat_message"]) > 0


@pytest.mark.asyncio
async def test_timeout_returns_friendly_message():
    from app.intake_agent import run_intake

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await run_intake("hello", [], "sess-004")

    assert result["profile_complete"] is False
    assert result["profile_data"] is None
    assert "again" in result["chat_message"].lower() or "sorry" in result["chat_message"].lower()


@pytest.mark.asyncio
async def test_conversation_history_is_included_in_messages():
    from app.intake_agent import run_intake

    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "Hello! What brings you here?"},
    ]
    reply = "What is your scale?"
    mock_resp = _make_mistral_response(reply)
    captured_payload: list[dict] = []

    async def capture_post(url: str, **kwargs: object) -> MagicMock:
        captured_payload.append(kwargs.get("json", {}))  # type: ignore[arg-type]
        return mock_resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=capture_post)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await run_intake("we target customers", history, "sess-005")

    assert len(captured_payload) == 1
    messages = captured_payload[0]["messages"]
    roles = [m["role"] for m in messages]
    assert roles[0] == "system"
    assert "user" in roles
    assert "assistant" in roles
    # New user turn is appended last
    assert messages[-1]["content"] == "we target customers"
