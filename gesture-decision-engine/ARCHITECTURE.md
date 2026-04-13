# Gesture Decision Engine — Architecture & Codebase Guide

> Personal reference for understanding and explaining this system in technical depth.

---

## What the system does (one paragraph)

This is an AI-powered sales qualification tool for a company called Gesture. A visitor opens the app and chats with an AI persona called Maya. Maya runs a structured intake conversation to collect four key facts about the visitor (who they're targeting, at what scale, toward what goal, and on what timeline). Once those are collected, a second AI call fires — this one has full product knowledge — and generates a tailored product recommendation with a confidence score and intent classification. A separate Sales Dashboard lets internal teams see all active sessions, read the structured profile data Maya collected, and understand where each lead is in the buying journey.

---

## High-level architecture

```
Browser (TypeScript SPA)
        │
        │  HTTP (JSON)
        ▼
FastAPI server  (Python, port 8000)
        │
        ├── POST /chat ──────────────────────────────────────────────────┐
        │        │                                                        │
        │   [intake phase]                              [recommendation phase]
        │   intake_agent.py                             recommendation_agent.py
        │   LLM Call 1 (temp 0.7)                      LLM Call 2 (temp 0.4)
        │   Collects profile fields                     + Extraction Call (temp 0.1)
        │   Emits PROFILE_COMPLETE sentinel             Generates structured decision
        │                                                                 │
        ├── GET  /sessions ───────────────────────────────────────────────┘
        ├── GET  /session/{id}/summary
        ├── DELETE /session/{id}
        └── GET  /health
        │
        ├── session_store.py   (in-memory dict, rate limiter)
        ├── models.py          (Pydantic data shapes)
        └── product_knowledge.py  (hard-coded product catalogue)
        │
        └── Serves frontend/dist/* as static files (SPA, no separate web server)
```

The frontend is a **single-page app bundled by esbuild** into one 13.8kb JS file. There is no React, no Vue — it is vanilla TypeScript with hand-written DOM manipulation. The backend serves both the API and the static files from the same FastAPI process, so there is only one server to run.

---

## Data flow: one full conversation

```
1. Browser loads /  → FastAPI serves frontend/dist/index.html + bundle.js
2. DOMContentLoaded → triggerGreeting() fires POST /chat {message: "hi"}
3. POST /chat → intake_agent.run_intake() → Mistral API (LLM 1)
   → returns {chat_message, profile_complete: false, profile_data: null}
4. User replies → POST /chat with same session_id
   → intake loop continues, collecting audience / scale / goal / timeline
5. When all 4 fields gathered → LLM 1 emits "PROFILE_COMPLETE\n{JSON}"
   → main.py parses the profile, calls update_profile(), set_phase("recommendation")
   → immediately calls run_recommendation() → Mistral API (LLM 2, temp 0.4)
   → if ---DECISION--- sentinel present: parse JSON inline
   → if sentinel missing or JSON malformed: fire _extract_decision_json() (LLM 2b, temp 0.1)
   → returns {chat_message, decision: {...}}
6. Response sent to browser:
   → chat panel renders Maya's recommendation text
   → decision panel renders vertical badge, confidence bar, intent tier, next questions
   → session data stored in _sessions dict (Python memory)
7. Follow-up messages → run_followup() → LLM 2 again (no decision JSON, just text)
```

---

## Backend files

### `app/models.py`

**What it is:** The single source of truth for all data shapes in the system. Written with Pydantic v2.

**Key classes:**

- `ChatRequest` — what the browser sends: `{message, session_id?}`
- `ChatResponse` — what the API returns: `{chat_message, session_id, phase, is_complete, decision}`
- `UserProfile` — the structured profile Maya builds: audience, scale, goal, timeline, existing_program, pain_point, company_type, raw_quotes. All fields are optional until intake completes.
- `SessionData` — everything stored server-side for one conversation: the message list (full LLM context), the profile, the phase, timestamps, intent score history, and `last_decision_raw` (a raw dict copy of the decision JSON, used by the Sales Dashboard without re-calling the LLM).
- `DecisionData` — the structured recommendation output: vertical, recommended campaign, confidence score (0–1 float), intent tier, reasoning, next questions.
- `SessionSummaryResponse` — what `GET /session/{id}/summary` returns, including a CRM summary sentence generated on the fly by a third Mistral call.

**Why Pydantic:** It gives you automatic type validation, serialisation to/from JSON, and `.model_dump()` for converting to plain dicts to pass into LLM prompts.

---

### `app/product_knowledge.py`

**What it is:** A hard-coded Python dict containing everything the recommendation LLM needs to know about Gesture's products. There is no database — this is the entire product catalogue baked into code.

**Structure:**
- `company` / `tagline` / `what_we_do` — company overview
- `verticals` — 4 verticals, each with: description, specific products, pricing, ideal customer profile, typical results, time to launch
  - `gifting` — Gift Finder, Occasion Engine, Gift-with-Purchase. Starts at $15/gift.
  - `loyalty` — Points-to-Gift, VIP Early Access, Re-engagement Kit. From $2k/month platform fee.
  - `brand_engagement` — Launch Kit, Pop-up Experience Box, Community Appreciation Drop. $10k–$50k per campaign.
  - `enterprise_rewards` — Milestone Recognition, Sales Performance Reward, Executive Gifting. From $5k/month.
- `how_it_works` — 5-step process (Connect → Curate → Choose → Deliver → Measure)
- `integrations` — Salesforce, HubSpot, Shopify, REST API
- `differentiators` — recipient choice model, white-label, global fulfilment, measurement, zero inventory risk
- `common_objections` — pre-written responses to "too expensive", "already have swag", "logistics concerns", etc.
- `pilot_program` — 90-day pilot terms

`get_knowledge_as_string()` serialises the whole dict to a JSON string that gets injected into the recommendation LLM's system prompt.

**Interview talking point:** This is a retrieval-augmented generation (RAG) pattern in its simplest form — instead of a vector database, the entire knowledge base is small enough to fit in a single system prompt. For a production system you would chunk it and retrieve only the relevant vertical.

---

### `app/session_store.py`

**What it is:** An in-memory key/value store for all active sessions. It is just a Python module-level dict — no Redis, no database.

```python
_sessions: dict[str, SessionData] = {}
_rate_limits: dict[str, deque] = {}
```

**Key functions:**

- `create_session(session_id)` — initialises a new `SessionData` and stores it
- `get_session(session_id)` → `SessionData | None`
- `update_session(session_id, updates: dict)` — generic key/value patching via `setattr`. Used to store `last_decision_raw` after recommendation fires.
- `add_message(session_id, role, content)` — appends to the message list that gets passed as conversation history to the LLM
- `get_conversation_history(session_id)` → `list[{role, content}]` — returns the message list formatted for the Mistral API
- `set_phase(session_id, phase)` — switches "intake" → "recommendation"
- `update_profile(session_id, profile_data)` — merges profile fields in. Marks `profile.is_complete = True` once all four required fields (audience, scale, goal, timeline) are non-null.
- `add_intent_score(session_id, score)` — appends to intent score history for the progression chart
- `list_sessions()` → `list[SessionData]` — returns all sessions, used by the Sales Dashboard
- `check_rate_limit(session_id) → bool` — sliding window limiter: 30 requests per 60 seconds per session. Uses a `deque` of timestamps; evicts entries older than the window and checks the count.

**Trade-off:** Everything is lost on server restart. For a production system you'd persist to Redis or Postgres. The benefit here is zero infrastructure — deploy one Python process and it works.

---

### `app/intake_agent.py`

**What it is:** LLM 1. Handles the early conversational phase, collecting the user's profile.

**How it works:**

1. Receives the user's latest message plus the full conversation history
2. Builds a messages array: `[system_prompt] + conversation_history + [current_user_message]`
3. Calls Mistral `mistral-small-latest` at `temperature=0.7` (creative/natural conversation tone), `max_tokens=400`
4. Parses the response:
   - If `"PROFILE_COMPLETE"` is in the reply → splits on the sentinel, parses the JSON block that follows → returns `{profile_complete: True, profile_data: {...}}`
   - Otherwise → returns `{profile_complete: False}` with just the chat text

**System prompt design:** Maya is instructed to ask only ONE question per message, keep replies short (2–3 sentences), and the moment all four required fields are known, to stop asking questions entirely and emit `PROFILE_COMPLETE` followed by a raw JSON object. There is an explicit "CRITICAL RULE" heading to make the instruction harder for the LLM to ignore.

**Turn-count pressure mechanism:** If the user has already sent 3+ messages and the LLM still hasn't fired `PROFILE_COMPLETE`, the code appends an injection to the user message: `"[You now have enough information. You MUST emit PROFILE_COMPLETE in this response.]"`. This is a reliability patch — LLMs sometimes keep asking questions indefinitely, and this forces completion by message 4–5.

**Error handling:**
- JSON parse fails after `PROFILE_COMPLETE` → graceful recovery message, returns `profile_complete: False` so the conversation continues
- `httpx.TimeoutException` → "Sorry, that took longer than expected" message
- Any other exception → generic apology

---

### `app/recommendation_agent.py`

**What it is:** LLM 2. The "expert" call that fires once intake is complete. Knows the full product catalogue and generates a structured recommendation.

**Two-call architecture — this is the key design:**

The challenge is that the backend needs both a *conversational response* (to show the user) and a *structured JSON object* (to populate the decision panel with badges, scores, etc.). Asking one LLM call to produce both reliably turned out to be difficult — Mistral Small often omitted the `---DECISION---` sentinel or malformed the JSON.

The solution is two separate calls:

**Call 1 — `run_recommendation()`** (`temperature=0.4`, `max_tokens=1000`)
- System prompt contains the full product knowledge and the user's profile
- Asks for a detailed, warm, specific recommendation
- Also asks the LLM to append `---DECISION---` followed by raw JSON
- If the sentinel is present and JSON parses → done, one call
- If the sentinel is missing or JSON is malformed → fall through to Call 2

**Call 2 — `_extract_decision_json()`** (`temperature=0.1`, `max_tokens=500`)
- A minimal extraction call: "Given this recommendation text and profile, output ONLY a raw JSON object with these fields"
- Temperature 0.1 = near-deterministic, focused output
- No conversation history, no persona — pure structured extraction
- If any required fields are missing from the JSON → patched from `_FALLBACK_DECISION` dict

**`build_recommendation_prompt(profile, product_knowledge)`** — constructs the full system prompt. Takes the profile dict and the knowledge base string. The prompt instructs Maya to: reference the prospect's exact words, name specific products, include real pricing, give realistic timelines, quote a relevant metric, and end with one specific next-step question.

**`run_followup()`** — for messages after the recommendation has been given. Uses the same LLM but with a shorter, simpler system prompt: "You have already recommended, now answer follow-up questions conversationally." Does not produce structured JSON — just a chat message. `temperature=0.4`, `max_tokens=400`.

---

### `app/main.py`

**What it is:** The FastAPI application. Wires together the session store, the two agents, intent scoring, and HTTP routing.

**Routes:**

#### `POST /chat`
The main endpoint. Full logic:

1. Validate: non-empty message, max 1000 chars
2. Session resolution: if `session_id` in request body, look it up (or create if not found); if absent, create new with `uuid4()`
3. Rate limit check: 30 req/60s per session → 429 if exceeded
4. Record user message: `add_message(session_id, "user", message)`
5. Compute intent score (keyword-based, see below) and append to history
6. **If phase == "intake":** call `run_intake()`. If `profile_complete=True` → `update_profile()`, `set_phase("recommendation")`, immediately call `run_recommendation()`. Concatenate both chat messages. Store `last_decision_raw` for the Sales Dashboard. Return `phase="recommendation"`.
7. **If phase == "recommendation":** call `run_followup()`. Return `phase="recommendation"`, `decision=None`.

**Intent scoring algorithm** (`_compute_intent_score`):
```
score = 0
if message contains high-intent words (pricing, cost, ready, contract, pilot, asap...) → +0.25
if message contains mid-intent words (interested, demo, tell me more, case study...)    → +0.12
if message_count > 4                                                                    → +0.15
if message_count > 8                                                                    → +0.10
capped at 1.0
```
This is purely keyword + depth based (no LLM call). It runs on every single message and builds the `intent_score_history` array that powers the progression dots in the Sales Dashboard.

#### `GET /session/{session_id}/summary`
Returns the full session summary. Additionally makes a **third Mistral call** (if `MISTRAL_API_KEY` is set) to generate a one-sentence CRM summary from the profile — intended to represent what a real system would write into Salesforce.

#### `GET /sessions`
Returns all sessions sorted by last-updated time. For each session, computes the most recent intent tier from score history, pulls `last_decision_raw` for vertical/confidence data, and returns the profile. This is what the Sales Dashboard polls.

#### `DELETE /session/{session_id}`
Removes the session from memory.

#### `GET /health`
`{"status": "ok", "version": "1.0.0"}` — used by the e2e test to check if the server is running.

**Static files:** `app.mount("/", StaticFiles(directory="frontend/dist", html=True))` — mounts last so all API routes take priority. This means one `uvicorn` process serves everything.

---

## Frontend files

### `frontend/src/types.ts`

All TypeScript interfaces. Defines the exact shape of every object that crosses the API boundary:

- `ChatRequest` / `ChatResponse` / `DecisionData` — mirror the Pydantic models exactly
- `UserProfile` — mirrors `UserProfile` from `models.py`
- `SessionState` — client-side tracking only (message count, has_asked_pricing, intent history)
- `SessionSummaryResponse` / `SessionListItem` — typed responses from `/summary` and `/sessions`
- `AppMode` — `"demo" | "customer" | "sales"` — the three view modes

This file has no runtime code — it is erased entirely at build time by TypeScript. Its only purpose is type safety during development.

---

### `frontend/src/api.ts`

Three async functions, each wrapping a `fetch()` call:

- `sendMessage(request: ChatRequest) → ChatResponse` — `POST /chat`
- `getSessionSummary(session_id) → SessionSummaryResponse` — `GET /session/{id}/summary`
- `getSessions() → SessionListItem[]` — `GET /sessions`

All three follow the same pattern: try/catch the network call (throws "Network error — is the server running?"), check `response.ok` (throws `Request failed (${status})`), return `response.json()`.

`BASE_URL` is an empty string — the frontend is served from the same origin as the API, so relative paths work automatically.

---

### `frontend/src/session.ts`

Client-side session state as a plain mutable object:

```typescript
export const state: SessionState = {
  session_id: null,        // set after first API response
  message_count: 0,        // incremented before each send
  session_start: Date.now(),
  has_asked_pricing: false, // set if user types pricing keywords
  current_phase: "intake",
  last_decision: null,
  intent_history: [],      // confidence scores from each decision
}
```

Exported functions:
- `updateFromResponse(response)` — reads `session_id` and `phase` from API response, pushes confidence score to `intent_history`
- `checkPricingKeywords(message)` — runs a simple keyword check on the user's input; sets `has_asked_pricing = true` (this could trigger UI hints in a richer version)
- `incrementMessageCount()` — called before each send; determines whether to show the "Session Summary" button
- `resetSession()` — called when "New Conversation" is clicked; zeroes everything

---

### `frontend/src/chat.ts`

Pure DOM manipulation for the chat thread. No state, no external dependencies.

- `appendUserMessage(content)` — creates a right-aligned bubble with the user's text
- `appendAssistantMessage(content, decision?)` — creates a left-aligned bubble with Maya's avatar ("M"). Splits content on double newlines and creates one `<p>` per paragraph. The `decision` parameter is accepted but not rendered here — rendering is done by `decision.ts`.
- `appendSystemMessage(content)` — centred system error message (shown on network failure)
- `showTypingIndicator()` / `hideTypingIndicator()` — animated three-dot indicator while waiting for API response
- `clearChat()` — wipes the thread on new conversation

---

### `frontend/src/decision.ts`

Manages the right-side decision panel (the "internal tool" side in Demo Mode).

- `showPlaceholder()` — shows the "Waiting for recommendation..." placeholder, hides the content div
- `updateDecision(decision: DecisionData)` — the main function:
  - Updates vertical badge (colour-coded: purple=gifting, blue=loyalty, orange=brand, green=enterprise)
  - Updates intent badge (grey=browsing, amber=engaged, green=high_intent)
  - Animates the confidence bar from its previous width to the new target percentage using `requestAnimationFrame`
  - Renders the reasoning text
  - Creates clickable "question chip" buttons from `next_questions` — clicking one pre-fills the chat input and sends it
- `addIntentDot(tier)` — appends a colour-coded dot to the intent timeline row below the decision panel (shows history of intent across turns)
- `onNextQuestionClick(callback)` — registers the callback that `main.ts` passes in to handle chip clicks

---

### `frontend/src/main.ts`

The application entry point and orchestrator. Everything is wired here.

**Mode switching:**
```typescript
function setMode(mode: AppMode): void {
  document.body.className = `mode-${mode}`;   // CSS does all the showing/hiding
  // ...activate correct nav button
  if (mode === "sales") refreshSessionsList(); // auto-load on switch
}
```
The entire layout is controlled by CSS rules on `body.mode-demo`, `body.mode-customer`, `body.mode-sales`. There is no JS show/hide logic.

**`handleSend(messageText)`** — the core send flow:
1. `checkPricingKeywords()` / `incrementMessageCount()`
2. Render user bubble, clear input, show typing indicator, disable input
3. Build `ChatRequest` (attach `session_id` if one exists)
4. `await sendMessage(req)` → on success: `updateFromResponse()`, `appendAssistantMessage()`, `updateDecision()`, `addIntentDot()`, show summary button if ≥3 messages in recommendation phase
5. On error: show system message
6. Always: re-enable input, focus

**`triggerGreeting()`** — fires on page load after 500ms delay, sends "hi" to get the first Maya message automatically.

**`setupPresets()`** — creates 4 preset buttons (Gifting, Loyalty, Brand, Enterprise). Each button calls `handleSend()` with a pre-written opening message, skipping the blank-input experience.

**`refreshSessionsList()`** — fetches `GET /sessions`, renders one card per session with vertical/intent badges and relative timestamp. Each card is clickable.

**`loadSessionDetail(sessionId, card)`** — fetches the session summary, then renders the full detail panel: profile table, pain point box, raw quotes, CRM summary, intent score progression dots, and a "Push to CRM → Salesforce" button.

**`showCrmToast(sessionId)`** — creates a slide-up toast notification simulating a Salesforce push. Auto-dismisses after 3.5 seconds using CSS transition.

**`showSummaryModal(summary)`** — renders the raw JSON summary in a modal overlay for the Demo/Customer view.

---

### `frontend/index.html`

The single HTML file. Key structural elements:

- `#mode-bar` (44px top bar) — three mode buttons: Demo, Customer View, Sales Dashboard
- `#app` (fills remaining viewport height)
  - `#left-wrapper` — contains the demo-mode label and the chat UI (`#chat-thread`, `#input-row`, preset buttons, summary button)
  - `#right-wrapper` — contains the demo-mode label and the decision panel (`#decision-placeholder`, `#decision-content` with all the badge/bar/reasoning elements)
  - `#sales-dashboard` — completely separate section with sessions sidebar and detail panel; hidden in demo/customer modes

CSS view-mode rules:
```css
body.mode-demo     → left(60%) + right(40%) visible; labels visible; dashboard hidden
body.mode-customer → left(100%); right hidden; presets hidden; labels hidden; dashboard hidden
body.mode-sales    → left hidden; right hidden; dashboard visible
```

This means switching modes is a single `className` change on `body` — the CSS handles everything declaratively.

---

## Test files

### `tests/test_intake.py`

Unit tests for `run_intake()`. Uses `unittest.mock.patch` to replace `httpx.AsyncClient` with an `AsyncMock`, so no real network calls are made.

5 tests:
1. `test_profile_not_complete_returns_chat_message` — LLM returns a question; assert `profile_complete=False`
2. `test_profile_complete_detected_and_parsed` — LLM returns `PROFILE_COMPLETE\n{JSON}`; assert all 4 profile fields parsed correctly
3. `test_malformed_json_after_profile_complete_returns_recovery_message` — LLM emits sentinel but garbled JSON; assert graceful recovery message, `profile_complete=False`
4. `test_timeout_returns_friendly_message` — mock raises `httpx.TimeoutException`; assert user-friendly reply
5. `test_conversation_history_is_included_in_messages` — captures the POST payload; asserts system/user/assistant messages all present in correct order

### `tests/test_recommendation.py`

Unit tests for `run_recommendation()`, `_extract_decision_json()`, and `run_followup()`. Same mock pattern.

8 tests:
1. `test_build_recommendation_prompt_includes_profile` — asserts pain_point and goal strings appear in the prompt
2. `test_build_recommendation_prompt_includes_product_knowledge` — asserts knowledge string injected
3. `test_build_recommendation_prompt_includes_decision_sentinel` — asserts `---DECISION---` in prompt
4. `test_decision_parsed_correctly_from_response` — inline sentinel path; full decision parsed and returned
5. `test_fallback_used_when_decision_json_is_malformed` — sentinel present but JSON invalid; fallback decision returned
6. `test_fallback_used_when_sentinel_missing` — no sentinel at all; extraction call fires (both mocked), fallback returned
7. `test_missing_fields_patched_from_fallback` — partial JSON (only 2 of 8 fields); missing fields filled from `_FALLBACK_DECISION`
8. `test_followup_returns_chat_message_only` — `run_followup()` returns just `chat_message`, no `decision` key

### `tests/test_e2e.py`

Integration tests that hit the real running server on `localhost:8000`. All tests are auto-skipped if the server is not up (`_server_running()` check).

5 tests:
1. `test_health_endpoint` — basic liveness check
2. `test_full_loyalty_conversation` — sends 4 real messages, asserts stable `session_id`, final phase is `recommendation`, decision has all 8 required fields with valid values
3. `test_session_summary_after_conversation` — runs same 4-turn flow, fetches summary, asserts `total_turns == 8` (4 user + 4 assistant), profile and intent progression present
4. `test_rate_limit_returns_429_after_30_rapid_requests` — fires 31 rapid requests on a fresh session, asserts at least one 429
5. `test_delete_session` — creates session, deletes it, confirms 404 on subsequent summary fetch

---

## Infrastructure files

### `Dockerfile`

Multi-stage build:
1. **Node 20 stage** — installs frontend dependencies, runs `npm run build` → produces `frontend/dist/`
2. **Python 3.11-slim stage** — copies the dist output from stage 1, installs Python dependencies, copies backend code, runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`

Result: one Docker image, one exposed port, zero external services required.

### `docker-compose.yml`

Single service definition. Maps port 8000, reads from `.env` for the API key, restarts unless stopped.

### `start.sh`

Local development shortcut:
```bash
cd frontend && npm run build && cd .. && uvicorn app.main:app --reload --port 8000
```
Builds the frontend bundle, then starts the backend with hot-reload.

### `requirements.txt`

Key dependencies:
- `fastapi` + `uvicorn[standard]` — web framework and ASGI server
- `pydantic` — data validation and serialisation
- `httpx` — async HTTP client for Mistral API calls
- `python-dotenv` — loads `MISTRAL_API_KEY` from `.env`
- `pytest` + `pytest-asyncio` — async unit test runner

---

## Key design decisions to discuss in an interview

**1. Two-LLM architecture with a dedicated extraction call**
The intake and recommendation are separate LLM calls with different temperatures (0.7 vs 0.4) and different token budgets. Within recommendation, a *third* micro-call at temperature 0.1 handles JSON extraction if the primary call fails to produce valid structured output. This three-call pattern solves a real reliability problem: models that are optimised for natural conversation often fail to produce well-formed JSON inline.

**2. Sentinel-based protocol for structured output**
Instead of using JSON-mode or function calling (which Mistral Small does support but with constraints), the system instructs the LLM to write a sentinel string (`PROFILE_COMPLETE`, `---DECISION---`) and then raw JSON. The backend splits on the sentinel. The benefit is transparency and debuggability — you can read the raw LLM output and see exactly what it produced. The cost is fragility, which the extraction fallback mitigates.

**3. In-memory session store**
All session state lives in a Python dict. This means zero infrastructure requirements — just run `uvicorn`. The trade-off is that sessions are lost on restart and the system cannot scale horizontally. For a production system you'd replace the `_sessions` dict with Redis calls, keeping the rest of the API identical.

**4. CSS-driven view modes**
The three UI modes (Demo, Customer, Sales) are controlled entirely by a single `className` on `document.body`. All the show/hide logic is declarative CSS, not JavaScript. This makes mode switching instantaneous, testable in static HTML, and zero risk of JS state diverging from UI state.

**5. Rate limiter per session using a sliding window deque**
Each session gets a `collections.deque` of request timestamps. On each request, timestamps older than 60 seconds are popped from the left, and the count is checked. If ≥30, reject with 429. This is O(1) amortised and requires no cron job or background task to clean up.

**6. esbuild over webpack/Rollup**
The 13.8kb bundle is produced by esbuild in ~6ms. No babel, no complex config — one command line. TypeScript strict mode (`strict: true`, `exactOptionalPropertyTypes: true`) provides compile-time safety without runtime overhead since it's erased at build time.
