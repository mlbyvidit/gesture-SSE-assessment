import type { DecisionData } from "./types";

interface ColorConfig {
  bg: string;
  text: string;
  label: string;
}

const VERTICAL_COLORS: Record<string, ColorConfig> = {
  gifting:           { bg: "#f3e8ff", text: "#7c3aed", label: "Gifting" },
  loyalty:           { bg: "#dbeafe", text: "#1d4ed8", label: "Loyalty" },
  brand_engagement:  { bg: "#fff7ed", text: "#c2410c", label: "Brand Engagement" },
  enterprise_rewards:{ bg: "#dcfce7", text: "#15803d", label: "Enterprise Rewards" },
  unknown:           { bg: "#f3f4f6", text: "#6b7280", label: "Unknown" },
};

const INTENT_COLORS: Record<string, ColorConfig> = {
  browsing:    { bg: "#f3f4f6", text: "#6b7280",  label: "Browsing" },
  engaged:     { bg: "#fef3c7", text: "#d97706",  label: "Engaged" },
  high_intent: { bg: "#dcfce7", text: "#15803d",  label: "High Intent" },
};

let nextQuestionCallback: ((q: string) => void) | null = null;
let previousScore = 0;
let panelAnimated = false;

function el<T extends HTMLElement>(id: string): T {
  return document.getElementById(id) as T;
}

export function showPlaceholder(): void {
  el("decision-placeholder").style.display = "flex";
  el("decision-content").style.display = "none";
}

export function updateDecision(decision: DecisionData): void {
  el("decision-placeholder").style.display = "none";
  const content = el("decision-content");
  content.style.display = "flex";

  if (!panelAnimated) {
    content.classList.add("panel-fade-in");
    panelAnimated = true;
  }

  // Phase badge
  el("phase-badge").textContent = "Recommendation";
  el("phase-badge").className = "phase-badge phase-recommendation";

  // Vertical badge
  const vKey = decision.vertical in VERTICAL_COLORS ? decision.vertical : "unknown";
  const vColor = VERTICAL_COLORS[vKey]!;
  const vBadge = el("vertical-badge");
  vBadge.textContent = vColor.label;
  vBadge.style.background = vColor.bg;
  vBadge.style.color = vColor.text;

  // Vertical description
  el("vertical-description").textContent = decision.vertical_description;

  // Recommended campaign
  el("campaign-name").textContent = decision.recommended_campaign;

  // Confidence score bar (animated)
  const targetPct = Math.round(decision.confidence_score * 100);
  const bar = el<HTMLElement>("confidence-bar-fill");
  const label = el("confidence-label");

  bar.style.width = `${previousScore}%`;
  label.textContent = `${targetPct}%`;
  requestAnimationFrame(() => {
    setTimeout(() => {
      bar.style.width = `${targetPct}%`;
      previousScore = targetPct;
    }, 50);
  });

  // Intent tier badge
  const iKey = decision.intent_tier in INTENT_COLORS ? decision.intent_tier : "browsing";
  const iColor = INTENT_COLORS[iKey]!;
  const iBadge = el("intent-badge");
  iBadge.textContent = iColor.label;
  iBadge.style.background = iColor.bg;
  iBadge.style.color = iColor.text;

  // Intent description
  el("intent-description").textContent = decision.intent_description;

  // Reasoning
  el("reasoning-text").textContent = decision.reasoning;

  // Next question chips
  const chipsContainer = el("next-questions-chips");
  chipsContainer.innerHTML = "";
  decision.next_questions.forEach((q) => {
    const chip = document.createElement("button");
    chip.className = "question-chip";
    chip.textContent = q;
    chip.addEventListener("click", () => {
      if (nextQuestionCallback) nextQuestionCallback(q);
      const original = chip.textContent;
      chip.textContent = "Copied!";
      chip.classList.add("question-chip--copied");
      setTimeout(() => {
        chip.textContent = original;
        chip.classList.remove("question-chip--copied");
      }, 1200);
    });
    chipsContainer.appendChild(chip);
  });
}

export function addIntentDot(tier: string): void {
  const timeline = el("intent-timeline");
  const dot = document.createElement("span");
  dot.className = "intent-dot";

  const iKey = tier in INTENT_COLORS ? tier : "browsing";
  const iColor = INTENT_COLORS[iKey]!;
  dot.style.background = iColor.text;
  dot.title = iColor.label;

  timeline.appendChild(dot);
}

export function onNextQuestionClick(callback: (question: string) => void): void {
  nextQuestionCallback = callback;
}
