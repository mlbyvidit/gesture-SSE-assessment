import type { DecisionData } from "./types";

function getThread(): HTMLElement {
  return document.getElementById("chat-thread") as HTMLElement;
}

function scrollToBottom(): void {
  const thread = getThread();
  thread.scrollTop = thread.scrollHeight;
}

function createBubbleWrapper(align: "left" | "right" | "center"): HTMLDivElement {
  const wrapper = document.createElement("div");
  wrapper.className = `msg-wrapper msg-${align}`;
  return wrapper;
}

export function appendUserMessage(content: string): void {
  const wrapper = createBubbleWrapper("right");

  const bubble = document.createElement("div");
  bubble.className = "bubble bubble-user";
  bubble.textContent = content;

  wrapper.appendChild(bubble);
  getThread().appendChild(wrapper);
  scrollToBottom();
}

export function appendAssistantMessage(content: string, _decision?: DecisionData): void {
  const wrapper = createBubbleWrapper("left");

  const avatar = document.createElement("div");
  avatar.className = "maya-avatar";
  avatar.textContent = "M";

  const bubble = document.createElement("div");
  bubble.className = "bubble bubble-assistant";

  const paragraphs = content.split(/\n\n+/);
  paragraphs.forEach((para) => {
    if (!para.trim()) return;
    const p = document.createElement("p");
    p.textContent = para.trim();
    bubble.appendChild(p);
  });

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  getThread().appendChild(wrapper);
  scrollToBottom();
}

export function appendSystemMessage(content: string): void {
  const wrapper = createBubbleWrapper("center");

  const msg = document.createElement("div");
  msg.className = "system-msg";
  msg.textContent = content;

  wrapper.appendChild(msg);
  getThread().appendChild(wrapper);
  scrollToBottom();
}

export function showTypingIndicator(): void {
  const existing = document.getElementById("typing-indicator");
  if (existing) return;

  const wrapper = createBubbleWrapper("left");
  wrapper.id = "typing-indicator";

  const avatar = document.createElement("div");
  avatar.className = "maya-avatar";
  avatar.textContent = "M";

  const bubble = document.createElement("div");
  bubble.className = "bubble bubble-assistant typing-bubble";
  bubble.innerHTML = `
    <span class="dot"></span>
    <span class="dot"></span>
    <span class="dot"></span>
  `;

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  getThread().appendChild(wrapper);
  scrollToBottom();
}

export function hideTypingIndicator(): void {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

export function clearChat(): void {
  getThread().innerHTML = "";
}
