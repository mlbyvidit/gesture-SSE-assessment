import time
from collections import deque
from typing import Optional

from app.models import SessionData, UserProfile

_sessions: dict[str, SessionData] = {}
_rate_limits: dict[str, deque] = {}

_RATE_LIMIT_MAX = 30
_RATE_LIMIT_WINDOW = 60.0  # seconds


def create_session(session_id: str) -> SessionData:
    now = time.time()
    session = SessionData(
        session_id=session_id,
        phase="intake",
        messages=[],
        profile=UserProfile(),
        created_at=now,
        last_updated=now,
        intent_score_history=[],
    )
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[SessionData]:
    return _sessions.get(session_id)


def update_session(session_id: str, updates: dict) -> SessionData:
    session = _sessions[session_id]
    for key, value in updates.items():
        setattr(session, key, value)
    session.last_updated = time.time()
    return session


def add_message(session_id: str, role: str, content: str) -> None:
    session = _sessions[session_id]
    session.messages.append({"role": role, "content": content})
    session.last_updated = time.time()


def get_conversation_history(session_id: str) -> list[dict]:
    session = _sessions[session_id]
    return [{"role": m["role"], "content": m["content"]} for m in session.messages]


def set_phase(session_id: str, phase: str) -> None:
    session = _sessions[session_id]
    session.phase = phase
    session.last_updated = time.time()


def update_profile(session_id: str, profile_data: dict) -> None:
    session = _sessions[session_id]
    profile = session.profile

    for key, value in profile_data.items():
        if hasattr(profile, key):
            setattr(profile, key, value)

    if all(
        getattr(profile, field) is not None
        for field in ("audience", "scale", "goal", "timeline")
    ):
        profile.is_complete = True

    session.last_updated = time.time()


def add_intent_score(session_id: str, score: float) -> None:
    session = _sessions[session_id]
    session.intent_score_history.append(score)
    session.last_updated = time.time()


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
    _rate_limits.pop(session_id, None)


def list_sessions() -> list[SessionData]:
    return list(_sessions.values())


def check_rate_limit(session_id: str) -> bool:
    now = time.time()
    if session_id not in _rate_limits:
        _rate_limits[session_id] = deque()

    timestamps = _rate_limits[session_id]

    # Evict timestamps outside the rolling window
    while timestamps and now - timestamps[0] > _RATE_LIMIT_WINDOW:
        timestamps.popleft()

    if len(timestamps) >= _RATE_LIMIT_MAX:
        return False

    timestamps.append(now)
    return True
