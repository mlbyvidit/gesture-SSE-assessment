export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface DecisionData {
  vertical: string;
  vertical_description: string;
  recommended_campaign: string;
  confidence_score: number;
  intent_tier: "browsing" | "engaged" | "high_intent";
  intent_description: string;
  reasoning: string;
  next_questions: string[];
}

export interface ChatResponse {
  chat_message: string;
  session_id: string;
  phase: "intake" | "recommendation";
  is_complete: boolean;
  decision: DecisionData | null;
}

export interface UserProfile {
  audience: string | null;
  scale: string | null;
  goal: string | null;
  timeline: string | null;
  existing_program: boolean | null;
  pain_point: string | null;
  company_type: string | null;
  raw_quotes: string[];
  is_complete: boolean;
}

export interface SessionState {
  session_id: string | null;
  message_count: number;
  session_start: number;
  has_asked_pricing: boolean;
  current_phase: "intake" | "recommendation";
  last_decision: DecisionData | null;
  intent_history: number[];
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  decision?: DecisionData;
}

export interface SessionSummaryResponse {
  session_id: string;
  total_turns: number;
  phase: string;
  profile: UserProfile;
  final_intent_tier: string | null;
  intent_score_progression: number[];
  top_vertical: string | null;
  crm_summary: string | null;
}

export interface SessionListItem {
  session_id: string;
  phase: "intake" | "recommendation";
  turn_count: number;
  last_updated: number;
  seconds_ago: number;
  vertical: string | null;
  intent_tier: string | null;
  confidence_score: number | null;
  profile: UserProfile;
}

export type AppMode = "demo" | "customer" | "sales";
