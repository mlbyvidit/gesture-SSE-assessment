import type { SessionState, ChatResponse, DecisionData } from "./types";

const PRICING_KEYWORDS = ["price", "pricing", "cost", "budget", "how much", "expensive"];

export const state: SessionState = {
  session_id: null,
  message_count: 0,
  session_start: Date.now(),
  has_asked_pricing: false,
  current_phase: "intake",
  last_decision: null,
  intent_history: [],
};

export function updateFromResponse(response: ChatResponse): void {
  state.session_id = response.session_id;
  state.current_phase = response.phase;
  if (response.decision) {
    state.last_decision = response.decision;
    state.intent_history.push(response.decision.confidence_score);
  }
}

export function checkPricingKeywords(message: string): void {
  const lower = message.toLowerCase();
  if (PRICING_KEYWORDS.some((kw) => lower.includes(kw))) {
    state.has_asked_pricing = true;
  }
}

export function incrementMessageCount(): void {
  state.message_count += 1;
}

export function resetSession(): void {
  state.session_id = null;
  state.message_count = 0;
  state.session_start = Date.now();
  state.has_asked_pricing = false;
  state.current_phase = "intake";
  state.last_decision = null;
  state.intent_history = [];
}
