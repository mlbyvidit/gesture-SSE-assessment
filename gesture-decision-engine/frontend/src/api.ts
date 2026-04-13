import type { ChatRequest, ChatResponse, SessionSummaryResponse, SessionListItem } from "./types";

const BASE_URL = "";

export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  } catch {
    throw new Error("Network error — is the server running?");
  }

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`Request failed (${response.status}): ${body}`);
  }

  return response.json() as Promise<ChatResponse>;
}

export async function getSessionSummary(session_id: string): Promise<SessionSummaryResponse> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/session/${encodeURIComponent(session_id)}/summary`);
  } catch {
    throw new Error("Network error — is the server running?");
  }

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`Request failed (${response.status}): ${body}`);
  }

  return response.json() as Promise<SessionSummaryResponse>;
}

export async function getSessions(): Promise<SessionListItem[]> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/sessions`);
  } catch {
    throw new Error("Network error — is the server running?");
  }

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`Request failed (${response.status}): ${body}`);
  }

  return response.json() as Promise<SessionListItem[]>;
}
