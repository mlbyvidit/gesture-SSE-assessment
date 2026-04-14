import { sendMessage, getSessionSummary, getSessions } from "./api";
import {
  appendUserMessage,
  appendAssistantMessage,
  appendSystemMessage,
  showTypingIndicator,
  hideTypingIndicator,
  clearChat,
} from "./chat";
import { updateDecision, addIntentDot, showPlaceholder, onNextQuestionClick } from "./decision";
import {
  state,
  updateFromResponse,
  checkPricingKeywords,
  incrementMessageCount,
  resetSession,
} from "./session";
import type { AppMode, SessionListItem, SessionSummaryResponse } from "./types";

// ─── Preset scenarios ────────────────────────────────

const PRESETS = [
  { label: "Gifting",    vertical: "gifting",             message: "I want to send personalised holiday gifts to my top 200 customers" },
  { label: "Loyalty",    vertical: "loyalty",             message: "We have 50,000 loyalty members and redemption rates are really low" },
  { label: "Brand",      vertical: "brand_engagement",    message: "We are launching a new product and want an experiential activation" },
  { label: "Enterprise", vertical: "enterprise_rewards",  message: "I need to reward our sales team at end of Q4 with something memorable" },
];

// ─── DOM helpers ─────────────────────────────────────

function el<T extends HTMLElement>(id: string): T {
  return document.getElementById(id) as T;
}

function getInput(): HTMLInputElement  { return el<HTMLInputElement>("message-input"); }
function getSendBtn(): HTMLButtonElement { return el<HTMLButtonElement>("send-btn"); }

function setSendingState(sending: boolean): void {
  getInput().disabled = sending;
  getSendBtn().disabled = sending;
  getSendBtn().classList.toggle("btn-loading", sending);
}

// ─── Mode switching ───────────────────────────────────

let currentMode: AppMode = "demo";

function setMode(mode: AppMode): void {
  currentMode = mode;
  document.body.className = `mode-${mode}`;

  document.querySelectorAll<HTMLButtonElement>(".mode-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset["mode"] === mode);
  });

  if (mode === "sales") {
    refreshSessionsList();
  }
}

function setupModeSwitcher(): void {
  document.querySelectorAll<HTMLButtonElement>(".mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.dataset["mode"] as AppMode;
      if (mode) setMode(mode);
    });
  });
}

// ─── Chat send flow ───────────────────────────────────

async function handleSend(messageText: string): Promise<void> {
  const trimmed = messageText.trim();
  if (!trimmed) return;

  checkPricingKeywords(trimmed);
  incrementMessageCount();
  appendUserMessage(trimmed);
  getInput().value = "";
  showTypingIndicator();
  setSendingState(true);

  try {
    const req = { message: trimmed } as import("./types").ChatRequest;
    if (state.session_id) req.session_id = state.session_id;
    const response = await sendMessage(req);

    hideTypingIndicator();
    updateFromResponse(response);
    appendAssistantMessage(response.chat_message, response.decision ?? undefined);

    if (response.decision) {
      updateDecision(response.decision);
      addIntentDot(response.decision.intent_tier);
    }

    if (response.phase === "recommendation" && state.message_count >= 3) {
      el("summary-btn").style.display = "inline-flex";
    }
  } catch (err) {
    hideTypingIndicator();
    const msg = err instanceof Error ? err.message : "Something went wrong.";
    appendSystemMessage(msg + " Please try again.");
  } finally {
    setSendingState(false);
    getInput().focus();
  }
}

async function triggerGreeting(): Promise<void> {
  showTypingIndicator();
  setSendingState(true);
  try {
    const response = await sendMessage({ message: "hi" });
    hideTypingIndicator();
    updateFromResponse(response);
    appendAssistantMessage(response.chat_message);
  } catch {
    hideTypingIndicator();
    appendSystemMessage("Unable to connect. Make sure the server is running on port 8000.");
  } finally {
    setSendingState(false);
    getInput().focus();
  }
}

// ─── Preset buttons ───────────────────────────────────

function setupPresets(): void {
  const container = el("preset-buttons");
  PRESETS.forEach(({ label, vertical, message }) => {
    const btn = document.createElement("button");
    btn.className = `preset-btn preset-${vertical}`;
    btn.textContent = label;
    btn.addEventListener("click", () => handleSend(message));
    container.appendChild(btn);
  });
}

// ─── New conversation ─────────────────────────────────

function setupNewConversation(): void {
  el("new-conversation-btn").addEventListener("click", () => {
    resetSession();
    clearChat();
    showPlaceholder();
    el("summary-btn").style.display = "none";
    setTimeout(triggerGreeting, 500);
  });
}

// ─── Session summary modal ────────────────────────────

function setupSummaryButton(): void {
  el("summary-btn").addEventListener("click", async () => {
    if (!state.session_id) return;
    try {
      const summary = await getSessionSummary(state.session_id);
      showSummaryModal(summary);
    } catch (err) {
      appendSystemMessage(err instanceof Error ? err.message : "Failed to load summary.");
    }
  });
}

function showSummaryModal(summary: SessionSummaryResponse): void {
  const existing = el("summary-modal");
  if (existing) existing.remove();

  const overlay = document.createElement("div");
  overlay.id = "summary-modal";
  overlay.className = "modal-overlay";

  const modal = document.createElement("div");
  modal.className = "modal";

  const title = document.createElement("h2");
  title.textContent = "Session Summary";

  const pre = document.createElement("pre");
  pre.className = "summary-pre";
  pre.textContent = JSON.stringify(summary, null, 2);

  const closeBtn = document.createElement("button");
  closeBtn.className = "modal-close";
  closeBtn.textContent = "Close";
  closeBtn.addEventListener("click", () => overlay.remove());
  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });

  modal.appendChild(title);
  modal.appendChild(pre);
  modal.appendChild(closeBtn);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}

// ─── Sales Dashboard ──────────────────────────────────

const VERTICAL_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  gifting:            { bg: "#f3e8ff", text: "#7c3aed", label: "Gifting" },
  loyalty:            { bg: "#dbeafe", text: "#1d4ed8", label: "Loyalty" },
  brand_engagement:   { bg: "#fff7ed", text: "#c2410c", label: "Brand Engagement" },
  enterprise_rewards: { bg: "#dcfce7", text: "#15803d", label: "Enterprise Rewards" },
};

const INTENT_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  browsing:    { bg: "#f3f4f6", text: "#6b7280", label: "Browsing" },
  engaged:     { bg: "#fef3c7", text: "#d97706", label: "Engaged" },
  high_intent: { bg: "#dcfce7", text: "#15803d", label: "High Intent" },
};

function timeAgo(secondsAgo: number): string {
  if (secondsAgo < 60)  return `${secondsAgo}s ago`;
  if (secondsAgo < 3600) return `${Math.floor(secondsAgo / 60)}m ago`;
  return `${Math.floor(secondsAgo / 3600)}h ago`;
}

async function refreshSessionsList(): Promise<void> {
  const list = el("sessions-list");
  list.innerHTML = `<div class="sessions-loading">Loading sessions...</div>`;

  let sessions: SessionListItem[];
  try {
    sessions = await getSessions();
  } catch {
    list.innerHTML = `<div class="sessions-loading">Failed to load sessions.</div>`;
    return;
  }

  if (sessions.length === 0) {
    list.innerHTML = `<div class="sessions-loading sessions-empty">No active sessions yet.<br>Send a message in Demo or Customer Mode first.</div>`;
    return;
  }

  list.innerHTML = "";
  sessions.forEach((s) => {
    const card = document.createElement("div");
    card.className = "session-card";
    card.dataset["sessionId"] = s.session_id;

    const shortId = s.session_id.slice(0, 8);
    const vKey = s.vertical ?? "";
    const vColor = VERTICAL_COLORS[vKey];
    const iKey = s.intent_tier ?? "browsing";
    const iColor = INTENT_COLORS[iKey] ?? INTENT_COLORS["browsing"]!;

    const verticalBadge = vColor
      ? `<span class="sc-badge" style="background:${vColor.bg};color:${vColor.text}">${vColor.label}</span>`
      : `<span class="sc-badge" style="background:#f3f4f6;color:#9ca3af">${s.phase === "intake" ? "Intake" : "Unknown"}</span>`;

    const intentBadge = `<span class="sc-badge" style="background:${iColor.bg};color:${iColor.text}">${iColor.label}</span>`;

    card.innerHTML = `
      <div class="sc-id">${shortId}&hellip;</div>
      <div class="sc-badges">${verticalBadge}${intentBadge}</div>
      <div class="sc-meta">${s.turn_count} turns &middot; ${timeAgo(s.seconds_ago)}</div>
    `;

    card.addEventListener("click", () => loadSessionDetail(s.session_id, card));
    list.appendChild(card);
  });
}

async function loadSessionDetail(sessionId: string, card: HTMLElement): Promise<void> {
  // Highlight selected card
  document.querySelectorAll(".session-card").forEach((c) => c.classList.remove("selected"));
  card.classList.add("selected");

  const panel = el("session-detail-panel");
  panel.innerHTML = `<div class="detail-loading">Loading session data...</div>`;

  let summary: SessionSummaryResponse;
  try {
    summary = await getSessionSummary(sessionId);
  } catch {
    panel.innerHTML = `<div class="detail-loading">Failed to load session.</div>`;
    return;
  }

  const p = summary.profile;
  const tier = summary.final_intent_tier ?? "browsing";
  const iColor = INTENT_COLORS[tier] ?? INTENT_COLORS["browsing"]!;

  // Vertical from session list data
  const sessions = await getSessions().catch(() => []);
  const sData = sessions.find((s) => s.session_id === sessionId);
  const vKey = sData?.vertical ?? "";
  const vColor = VERTICAL_COLORS[vKey];
  const confidence = sData?.confidence_score;

  const verticalHtml = vColor
    ? `<span class="detail-badge" style="background:${vColor.bg};color:${vColor.text}">${vColor.label}</span>`
    : `<span class="detail-badge" style="background:#f3f4f6;color:#9ca3af">Not determined</span>`;

  const intentHtml = `<span class="detail-badge" style="background:${iColor.bg};color:${iColor.text}">${iColor.label}</span>`;

  const profileRows = [
    ["Audience",   p.audience],
    ["Scale",      p.scale],
    ["Goal",       p.goal],
    ["Timeline",   p.timeline],
    ["Company",    p.company_type],
    ["Existing programme", p.existing_program === null ? null : (p.existing_program ? "Yes" : "No")],
  ]
    .filter(([, v]) => v !== null && v !== undefined)
    .map(([k, v]) => `<tr><td class="profile-key">${k}</td><td class="profile-val">${v}</td></tr>`)
    .join("");

  const quotesHtml = p.raw_quotes.length
    ? p.raw_quotes.map((q) => `<blockquote class="raw-quote">"${q}"</blockquote>`).join("")
    : `<p class="no-data">No quotes captured yet.</p>`;

  const crmHtml = summary.crm_summary
    ? `<p class="crm-note">${summary.crm_summary}</p>`
    : `<p class="no-data">Generate by viewing full summary.</p>`;

  const isHighIntent = tier === "high_intent";

  panel.innerHTML = `
    <div class="detail-header">
      <div class="detail-session-id">${sessionId.slice(0, 8)}&hellip;${sessionId.slice(-4)}</div>
      <div class="detail-meta">${summary.total_turns} turns &middot; ${summary.phase}</div>
    </div>

    <div class="detail-section">
      <div class="detail-section-label">Vertical &amp; Intent</div>
      <div class="detail-badges-row">${verticalHtml}${intentHtml}${confidence !== null && confidence !== undefined ? `<span class="detail-score">${Math.round(confidence * 100)}% confidence</span>` : ""}</div>
    </div>

    <div class="detail-section">
      <div class="detail-section-label">User Profile</div>
      ${p.pain_point ? `<div class="pain-point-box">Pain point: "${p.pain_point}"</div>` : ""}
      <table class="profile-table">${profileRows}</table>
    </div>

    <div class="detail-section">
      <div class="detail-section-label">Raw Quotes</div>
      ${quotesHtml}
    </div>

    <div class="detail-section">
      <div class="detail-section-label">CRM Summary</div>
      ${crmHtml}
    </div>

    <div class="detail-section">
      <div class="detail-section-label">Intent Score Progression</div>
      <div class="score-dots">
        ${summary.intent_score_progression.map((s) => {
          const t = s >= 0.65 ? "high_intent" : s >= 0.35 ? "engaged" : "browsing";
          const c = (INTENT_COLORS[t] ?? INTENT_COLORS["browsing"]!).text;
          return `<span class="score-dot" style="background:${c}" title="${Math.round(s * 100)}%"></span>`;
        }).join("")}
      </div>
    </div>

    <div class="crm-action-bar">
      ${isHighIntent
        ? `<p class="crm-action-note">This prospect is <strong>High Intent</strong>. In production this would trigger automatically.</p>`
        : `<p class="crm-action-note">In production, High Intent leads are pushed to CRM automatically via Pub/Sub.</p>`}
      <button class="push-crm-btn" id="push-crm-btn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.5a19.79 19.79 0 01-3-8.59A2 2 0 012.08 1h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.09 8.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"></path></svg>
        Push to CRM &rarr; Salesforce
      </button>
    </div>
  `;

  el("push-crm-btn").addEventListener("click", () => showCrmToast(sessionId));
}

function showCrmToast(sessionId: string): void {
  const existing = document.getElementById("crm-toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.id = "crm-toast";
  toast.className = "crm-toast";
  toast.innerHTML = `
    <div class="toast-icon">✓</div>
    <div class="toast-text">
      <strong>Lead pushed to Salesforce</strong>
      <span>Account Executive notified &middot; Session ${sessionId.slice(0, 8)}&hellip;</span>
    </div>
  `;

  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("toast-visible"));
  setTimeout(() => {
    toast.classList.remove("toast-visible");
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}

// ─── Bootstrap ───────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  setMode("demo");
  setupModeSwitcher();
  showPlaceholder();
  setupPresets();
  setupNewConversation();
  setupSummaryButton();

  onNextQuestionClick((question) => {
    navigator.clipboard.writeText(question).catch(() => {});
  });

  getInput().addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(getInput().value);
    }
  });

  getSendBtn().addEventListener("click", () => handleSend(getInput().value));

  el("dashboard-refresh-btn").addEventListener("click", refreshSessionsList);

  setTimeout(triggerGreeting, 500);
});
