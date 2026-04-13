from __future__ import annotations

import time
from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None


class DecisionData(BaseModel):
    vertical: str
    vertical_description: str
    recommended_campaign: str
    confidence_score: float
    intent_tier: str  # "browsing" | "engaged" | "high_intent"
    intent_description: str
    reasoning: str
    next_questions: list[str]


class ChatResponse(BaseModel):
    chat_message: str
    session_id: str
    phase: str  # "intake" | "recommendation"
    is_complete: bool
    decision: Optional[DecisionData] = None


class UserProfile(BaseModel):
    audience: Optional[str] = None        # "customers" | "employees" | "partners" | "brand"
    scale: Optional[str] = None           # "small" | "medium" | "large" | "enterprise"
    goal: Optional[str] = None            # "retention" | "recognition" | "engagement" | "acquisition"
    timeline: Optional[str] = None        # "immediate" | "planned" | "exploring"
    existing_program: Optional[bool] = None
    pain_point: Optional[str] = None
    company_type: Optional[str] = None
    raw_quotes: list[str] = []
    is_complete: bool = False


class SessionData(BaseModel):
    session_id: str
    phase: str = "intake"                 # "intake" | "recommendation"
    messages: list[dict] = []             # full conversation history for LLM context
    profile: UserProfile = Field(default_factory=UserProfile)
    created_at: float = Field(default_factory=time.time)
    last_updated: float = Field(default_factory=time.time)
    intent_score_history: list[float] = []
    last_decision_raw: Optional[dict] = None  # stored when recommendation fires


class SessionSummaryResponse(BaseModel):
    session_id: str
    total_turns: int
    phase: str
    profile: UserProfile
    final_intent_tier: Optional[str]
    intent_score_progression: list[float]
    top_vertical: Optional[str]
    crm_summary: Optional[str]
