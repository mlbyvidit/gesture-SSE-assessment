# Architecture & Codebase Reference

Personal technical reference for understanding every part of this system — written to support a detailed technical conversation about how it works, why decisions were made, and what trade-offs exist.

---

## System overview in one paragraph

This is an AI-powered sales qualification tool for a company called Gesture. A visitor opens the app and chats with an AI persona called Maya. Maya runs a structured intake conversation to collect four key facts (who they're targeting, at what scale, toward what goal, on what timeline). Once those are collected, a second LLM call fires with full product knowledge and generates a tailored product recommendation, a confidence score, and an intent classification. A separate Sales Dashboard lets internal teams see all active sessions, read the structured profile data Maya collected, and understand where each lead is in the buying journey. Everything runs in a single Python process — no database, no message queue, no separate web server.

---

## Architecture diagram

```
Browser (TypeScript SPA — vanilla, no framework)
        │
        │  HTTP JSON over the same origin (relative URLs)
        ▼
FastAPI server  (Python 3.11, Uvicorn, port 8000)
        │
        ├── POST /chat ──────────── main.py orchestrates:
        │        │                       │
        │   [phase == intake]        [phase == recommendation]
        │   intake_agent.py          recommendation_agent.py
        │   LLM Call 1               LLM Call 2a (chat, temp 0.4)
        │   temp 0.7, 400 tok        + LLM Call 2b (JSON extract, temp 0.1)
        │   Collects 4 profile fields Generates structured DecisionData
        │   Emits PROFILE_COMPLETE   Emits ---DECISION--- (or falls back)
        │
        ├── GET  /sessions           list_sessions() → all SessionData
        ├── GET  /session/{id}/summary  + LLM Call 3 (CRM note, temp 0.3)
        ├── DELETE /session/{id}
        └── GET  /health
        │
        └── GET /* → StaticFiles(frontend/dist/)   ← mounted last, lowest priority

Internal modules:
  session_store.py     — Python dict, no external DB
  models.py            — Pydantic v2 data shapes
  product_knowledge.py — static dict, injected into LLM prompt
```

The frontend is a **single-page app bundled by esbuild** into one 13.8 kb JS file. No React, no Vue — vanilla TypeScript with direct DOM manipulation. FastAPI serves both the API routes and the compiled static files from the same process and port, so there is only one server to start.

---

## Full data flow — one complete conversation

```
1.  Browser loads http://localhost:8000
    → FastAPI serves frontend/dist/index.html + bundle.js

2.  DOMContentLoaded fires in main.ts
    → setTimeout(triggerGreeting, 500)
    → POST /chat {message: "hi"}

3.  POST /chat (first message, no session_id)
    → session_id = uuid4(), create_session(session_id)
    → check_rate_limit() → OK
    → add_message(session_id, "user", "hi")
    → _compute_intent_score("hi", 1) → 0.0 → add_intent_score()
    → phase == "intake" → run_intake("hi", [], session_id)
    → Mistral API call (LLM 1, temp 0.7)
    → reply has no PROFILE_COMPLETE → {profile_complete: False, chat_message: "Hey there..."}
    → add_message(session_id, "assistant", "Hey there...")
    → return ChatResponse {phase: "intake", decision: null}

4.  Browser: updateFromResponse() stores session_id in state
    appendAssistantMessage() renders Maya's greeting

5.  User types and sends (e.g. "we have 50k loyalty members and churn is high")
    → POST /chat {message: "...", session_id: "..."}
    → same session retrieved, message added to history
    → intent score computed: no high-intent keywords → 0.0
    → run_intake(message, conversation_history, session_id)
    → LLM 1 receives [system_prompt, "hi", "Hey there...", current_message]
    → still gathering info → returns question about audience

6.  Turns continue until LLM 1 has all 4 fields (audience, scale, goal, timeline)
    → LLM 1 emits: "Great, I have what I need...\nPROFILE_COMPLETE\n{JSON}"
    → intake_agent.py splits on "PROFILE_COMPLETE"
    → json.loads() on the JSON block → profile_data dict
    → returns {profile_complete: True, chat_message: "Great, I have what I need...", profile_data: {...}}

7.  main.py receives profile_complete == True:
    → update_profile(session_id, profile_data)
    → set_phase(session_id, "recommendation")
    → immediately calls run_recommendation(profile_data, conversation_history, session_id)

8.  run_recommendation():
    → builds system prompt: product knowledge + validated profile JSON
    → Mistral API call (LLM 2, temp 0.4, 1000 tokens)
    → if ---DECISION--- sentinel in reply → parse JSON inline
    → if sentinel missing or JSON malformed → _extract_decision_json()
        → Mistral API call (LLM 2b, temp 0.1, 500 tokens)
        → "given this recommendation text, output ONLY a JSON object"
        → parse result, patch any missing fields from _FALLBACK_DECISION
    → return {chat_message: "Based on your situation...", decision: {...}}

9.  main.py:
    → combined_message = intake closing text + "\n\n" + recommendation text
    → add_message(session_id, "assistant", combined_message)
    → update_session(session_id, {"last_decision_raw": decision_raw})
    → return ChatResponse {phase: "recommendation", is_complete: True, decision: DecisionData}

10. Browser:
    → appendAssistantMessage() renders the combined message
    → updateDecision() populates the decision panel (badge, bar, chips)
    → addIntentDot() appends a coloured dot to the intent timeline
    → if message_count >= 3 → show "View Summary" button
```

---

## Backend files

---

### `app/models.py`

The single source of truth for all data shapes. Written with Pydantic v2. Every class here corresponds to something that either crosses the API boundary or lives in the session store.

**`ChatRequest`**
What the browser sends on every message. Two fields: `message` (non-empty string, max 1000 chars enforced by Pydantic `Field`) and optional `session_id`. If `session_id` is absent, the backend creates a new session.

**`DecisionData`**
The structured output of the recommendation LLM. Eight fields: `vertical` (one of four strings), `vertical_description`, `recommended_campaign`, `confidence_score` (float 0.0–1.0, clamped in main.py), `intent_tier` ("browsing" | "engaged" | "high_intent"), `intent_description`, `reasoning`, and `next_questions` (list of strings).

**`ChatResponse`**
What the API returns. `chat_message` (Maya's text), `session_id`, `phase` ("intake" or "recommendation"), `is_complete` (bool), and `decision` (null during intake, `DecisionData` when recommendation fires).

**`UserProfile`**
The structured profile Maya builds over the intake conversation. All fields are optional initially. The four required fields (audience, scale, goal, timeline) must all be non-null for `is_complete` to become True. Also stores: `existing_program` (bool or null), `pain_point` (their exact words), `company_type`, and `raw_quotes` (verbatim strings from the conversation).

**`SessionData`**
Everything stored server-side for one conversation: `session_id` (UUID), `phase`, `messages` (the exact array passed as conversation history to the LLM), `profile` (a `UserProfile` instance), timestamps, `intent_score_history` (list of floats, one per user message), and `last_decision_raw` (dict copy of the decision JSON stored when recommendation fires, used by the Sales Dashboard without re-calling the LLM).

**`SessionSummaryResponse`**
What `GET /session/{id}/summary` returns. Contains the full profile, `final_intent_tier`, `intent_score_progression`, and `crm_summary` (a Mistral-generated one-sentence CRM note).

**Why Pydantic v2:** Automatic JSON validation on input (wrong types raise 422 before the route body runs), `.model_dump()` for converting profile to a plain dict to inject into LLM prompts, and serialisation for API responses.

---

### `app/product_knowledge.py`

A hard-coded Python dict containing everything the recommendation LLM needs to know about Gesture's products. There is no database — the entire product catalogue lives in this file.

**Why not a database or vector store?** The knowledge base is small enough (~3 kb of JSON) to fit in a single system prompt without hitting Mistral Small's context limit. For a production system with hundreds of products, you would chunk this and store in a vector database (Pinecone, Vertex AI), retrieving only the top-k chunks relevant to the detected vertical. That is the standard RAG architecture. What exists here is the simplest possible version: retrieve everything, inject everything.

**Structure:**
- `company` / `tagline` / `what_we_do` — company-level context
- `verticals` — four keys (gifting, loyalty, brand_engagement, enterprise_rewards), each with: `description`, `products` (list of 3 specific named products), `pricing` (real numbers), `ideal_customer`, `typical_results` (the metrics Maya quotes), `time_to_launch`
- `how_it_works` — five-step platform flow (Connect → Curate → Choose → Deliver → Measure)
- `integrations` — Salesforce, HubSpot, Shopify, REST API
- `differentiators` — five reasons to choose Gesture
- `common_objections` — pre-written responses to: too_expensive, already_have_swag, logistics_complexity, integration_concerns, scale_concerns. The LLM uses these to handle pushback without hallucinating
- `pilot_program` — 90-day pilot terms

`get_knowledge_as_string()` serialises the whole dict to JSON and returns it. Called inside `run_recommendation()` and injected directly into the system prompt.

---

### `app/session_store.py`

An in-memory key/value store for all active sessions. Two module-level Python dicts — no external dependencies.

```python
_sessions: dict[str, SessionData] = {}     # session_id → SessionData
_rate_limits: dict[str, deque] = {}        # session_id → deque of timestamps
```

These are module-level globals that persist for the lifetime of the server process and are shared across all async requests.

**`create_session(session_id)`** — initialises a `SessionData` with defaults and stores it.

**`get_session(session_id)`** — `_sessions.get(session_id)` — returns `None` if not found.

**`update_session(session_id, updates: dict)`** — generic field patching via `setattr`. Used to store `last_decision_raw` after recommendation fires.

**`add_message(session_id, role, content)`** — appends `{role, content}` to `session.messages`. This list is the full conversation history passed to the Mistral API on every call, so the LLM always has complete context.

**`get_conversation_history(session_id)`** — returns the message list in Mistral API format: `[{role, content}, ...]`.

**`set_phase(session_id, phase)`** — switches "intake" → "recommendation". Called immediately after `profile_complete == True`.

**`update_profile(session_id, profile_data)`** — merges the LLM-extracted profile dict into the `UserProfile` instance field by field. Sets `profile.is_complete = True` once all four required fields (audience, scale, goal, timeline) are non-null.

**`add_intent_score(session_id, score)`** — appends to `intent_score_history`. Builds the progression array shown in the Sales Dashboard.

**`list_sessions()`** — returns all `SessionData` values. Used by `GET /sessions`.

**`delete_session(session_id)`** — removes from both dicts. Idempotent via `.pop(key, None)`.

**Rate limiter — `check_rate_limit(session_id) → bool`**

Sliding window algorithm using `collections.deque`:
1. Get or create the deque for this session
2. Pop timestamps from the left while older than 60 seconds (lazy eviction)
3. If len ≥ 30 → return False (→ 429)
4. Append current timestamp, return True

O(1) amortised. No background task needed — expired entries are cleaned up on each incoming request. The deque is bounded in practice because expired entries are evicted before the count is checked.

**Production upgrade path:** Replace the `_sessions` dict with Redis calls (`redis.asyncio`), keeping all function signatures identical. Session TTL can be managed with Redis key expiry. Switching storage requires changing only this one file.

---

### `app/intake_agent.py`

LLM 1. Handles the conversational intake phase. Its only job is to collect four profile fields through natural conversation and emit a structured signal when done.

**The system prompt** defines Maya as a "warm intake specialist". Key instructions:
- Ask only ONE question per message — never two
- Keep replies to 2–3 sentences during intake
- Do NOT mention product names, pricing, or campaign details — the intake agent is deliberately product-blind to prevent premature pitching and hallucinated recommendations
- The moment all four fields are known: stop asking, write a warm closing message, then emit `PROFILE_COMPLETE` followed by a raw JSON object on the very next line

The JSON the LLM produces after `PROFILE_COMPLETE`:
```json
{
  "audience": "customers|employees|partners|brand",
  "scale": "small|medium|large|enterprise",
  "goal": "retention|recognition|engagement|acquisition",
  "timeline": "immediate|planned|exploring",
  "existing_program": true|false|null,
  "pain_point": "their exact words or null",
  "company_type": "type or null",
  "raw_quotes": ["verbatim quote 1", "verbatim quote 2"]
}
```

**`run_intake(user_message, conversation_history, session_id)`**

Builds the messages array: `[system_prompt] + conversation_history + [current_user_message]`. Calls Mistral at `temperature=0.7` (warmer, more conversational), `max_tokens=400`.

**Turn-count pressure mechanism:** If the user has already sent 3+ messages and `PROFILE_COMPLETE` still hasn't appeared, the code appends an invisible instruction to the current user message:
```
[You now have enough information. You MUST emit PROFILE_COMPLETE in this response. Do not ask another question.]
```
This is a reliability patch for a real observed problem: LLMs sometimes keep gathering information indefinitely. The injection forces completion by message 4–5 at the latest, invisibly to the user.

**Parsing the response:**
1. If `"PROFILE_COMPLETE"` in reply: split on sentinel, `chat_part` = text before, `json_part` = text after
2. Strip markdown code fences if present (Mistral sometimes wraps JSON in ` ```json ``` ` despite being told not to)
3. `json.loads(json_part)` → if success: `{profile_complete: True, chat_message, profile_data}`
4. `JSONDecodeError` → log error, return graceful recovery message, `profile_complete: False`

**Error handling:** `httpx.TimeoutException` → user-friendly retry message. Any other exception → generic apology. Neither exposes a stack trace to the user.

---

### `app/recommendation_agent.py`

LLM 2. Fires once intake is complete. Has full product knowledge and generates a warm, specific, priced recommendation plus a structured `DecisionData` object.

**`build_recommendation_prompt(profile, product_knowledge)`**

Constructs the system prompt. Injects: (1) the validated `UserProfile` as indented JSON — the LLM reads the prospect's exact pain point and situation before writing a word; (2) the full `PRODUCT_KNOWLEDGE` string; (3) instructions to name specific products, cite real pricing and timelines, quote a relevant metric, handle likely objections, and end with one next-step question; (4) the `---DECISION---` sentinel instruction and exact JSON schema.

**Two-call architecture — the core engineering decision**

The backend needs two things from this phase: a conversational message to show the user, and a structured JSON object to populate the decision panel. Asking one LLM call to produce both reliably in a single response is fragile — Mistral Small often omits the sentinel or produces malformed inline JSON.

**Call 1 — `run_recommendation()`** (`temperature=0.4`, `max_tokens=1000`)
- `chat_part = reply.strip()` is set **before** any sentinel parsing — this preserves clean chat text regardless of what happens to the JSON parsing
- If `---DECISION---` present and JSON parses cleanly → return immediately, one call total
- If sentinel missing or JSON malformed → fall through to Call 2

**Call 2 — `_extract_decision_json(chat_reply, profile, api_key, session_id)`** (`temperature=0.1`, `max_tokens=500`)
- Minimal extraction call — no persona, no history, no product knowledge
- Prompt: "Given this recommendation text and profile, output ONLY a raw JSON object with these exact fields"
- Temperature 0.1 = near-deterministic. Very unlikely to add surrounding text or markdown at this temperature
- Strips markdown fences defensively before parsing
- Missing required fields → patched from `_FALLBACK_DECISION`
- If the call itself fails → returns `_FALLBACK_DECISION` in full

**`_FALLBACK_DECISION`** — hardcoded dict with safe defaults for all 8 required fields. Ensures the decision panel always has something to render even on complete LLM failure. `confidence_score: 0.5`, `intent_tier: "engaged"`.

**Missing fields patch pattern:**
```python
missing = _REQUIRED_DECISION_FIELDS - decision_data.keys()
for field in missing:
    decision_data[field] = _FALLBACK_DECISION[field]
```
This means partial JSON is always safe — whatever the LLM did produce is preserved, only gaps are filled.

**`run_followup(user_message, conversation_history, profile, session_id)`**

For messages sent after the recommendation. Simpler system prompt: "You have already recommended, now answer follow-up questions conversationally." No structured JSON. Uses `conversation_history[-6:]` (sliding window) to prevent unbounded context growth. `temperature=0.4`, `max_tokens=400`.

---

### `app/main.py`

The FastAPI application. Wires together the session store, the two agents, intent scoring, and all HTTP routing.

**Intent scoring — `_compute_intent_score(message, message_count) → float`**

Runs on every user message. Pure keyword + depth heuristic, no LLM call.

```
+0.25  high-intent keywords: pricing, price, cost, budget, how much, ready,
        start, contract, timeline, pilot, integrate, asap, urgent, next steps, sign up
+0.12  mid-intent keywords: interested, considering, demo, example,
        tell me more, how does, what is, case study
+0.15  if message_count > 4  (engagement depth bonus)
+0.10  if message_count > 8  (high engagement depth bonus)
capped at 1.0
```

Tier mapping: 0.00–0.34 → "browsing", 0.35–0.64 → "engaged", 0.65–1.00 → "high_intent". Score appended to `intent_score_history` on every turn.

**`POST /chat` — full route logic**

1. Validate: `message.strip()` non-empty, length ≤ 1000
2. Session resolution: if `session_id` in request → `get_session()` (or create if not found, supports reconnecting); if absent → `uuid4()` + `create_session()`
3. `check_rate_limit()` → 429 if exceeded
4. `add_message(session_id, "user", message)` — before the LLM call so history includes the current message
5. `_compute_intent_score()` → `add_intent_score()`
6. **Intake branch** (`phase == "intake"`): `run_intake()` → if `profile_complete == True`: `update_profile()` → `set_phase("recommendation")` → `run_recommendation()` (in the same request, no second round-trip) → `update_session({"last_decision_raw": ...})` → `return ChatResponse(phase="recommendation", is_complete=True, decision=DecisionData)`
7. **Recommendation branch** (`phase == "recommendation"`): `run_followup()` → `return ChatResponse(phase="recommendation", decision=None)`

**`GET /session/{session_id}/summary`**

Returns `SessionSummaryResponse`. Makes a **third Mistral call** (`temperature=0.3`, `max_tokens=100`) to generate a one-sentence CRM summary from the profile. If the call fails, `crm_summary=None` and the endpoint still returns 200.

**`GET /sessions`**

All sessions sorted by `last_updated` descending. For each: pulls `last_decision_raw` for vertical/confidence, computes current intent tier from score history, includes full profile. Used by the Sales Dashboard.

**`DELETE /session/{session_id}`** → `{"deleted": true}`

**`GET /health`** → `{"status": "ok", "version": "1.0.0"}`

**Static file serving:**
```python
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```
Mounted last — all API routes take priority. `html=True` makes requests to unknown paths serve `index.html`. The `npm run build` script copies `index.html` into `dist/` so it is available at `/`.

---

## Frontend files

---

### `frontend/src/types.ts`

All TypeScript interface definitions. Zero runtime code — completely erased at compile time. Its only purpose is type safety during development.

Mirrors the Pydantic models exactly: `ChatRequest`, `ChatResponse`, `DecisionData`, `UserProfile`, `SessionSummaryResponse`, `SessionListItem`. Also defines `SessionState` (client-side tracking only, not on the server) and `AppMode = "demo" | "customer" | "sales"`.

TypeScript config uses `strict: true` and `exactOptionalPropertyTypes: true`. The `exactOptionalPropertyTypes` flag means you cannot assign `undefined` to an optional property — you must omit the key entirely. This is why `ChatRequest` is built conditionally in `main.ts`:
```typescript
const req = { message: trimmed } as ChatRequest;
if (state.session_id) req.session_id = state.session_id;
```

---

### `frontend/src/api.ts`

Three async functions wrapping `fetch()` with consistent error handling.

- `sendMessage(request: ChatRequest) → Promise<ChatResponse>` — `POST /chat`
- `getSessionSummary(session_id) → Promise<SessionSummaryResponse>` — `GET /session/{id}/summary`
- `getSessions() → Promise<SessionListItem[]>` — `GET /sessions`

All three: try/catch the network call → throw "Network error"; check `response.ok` → throw "Request failed (${status})"; return `response.json()`.

`BASE_URL` is `""` (empty string). Because the frontend is served from the same origin as the API (same host, same port 8000), all fetch calls use relative URLs. The same build works in local dev and Docker with no configuration.

---

### `frontend/src/session.ts`

Client-side session state as a mutable module-level object — the single source of truth for what the browser knows about the current conversation.

```typescript
export const state: SessionState = {
  session_id: null,           // null until first API response
  message_count: 0,           // incremented before each send
  session_start: Date.now(),
  has_asked_pricing: false,   // set if user mentions price/cost/budget
  current_phase: "intake",    // mirrors the server's phase field
  last_decision: null,
  intent_history: [],         // confidence scores from decision responses
}
```

`updateFromResponse(response)` — updates `session_id`, `current_phase`, pushes confidence score to `intent_history`.

`checkPricingKeywords(message)` — keyword check on outgoing message, sets `has_asked_pricing = true`.

`incrementMessageCount()` — called before each send. The count reaching 3 in recommendation phase triggers the "View Summary" button.

`resetSession()` — zeroes everything. Next `handleSend()` has no `session_id`, so the server creates a new session.

---

### `frontend/src/chat.ts`

Pure DOM manipulation for the chat thread. No state, no external dependencies beyond the `DecisionData` type import.

`appendUserMessage(content)` — right-aligned bubble, `textContent = content` (safe, no XSS risk).

`appendAssistantMessage(content, decision?)` — left-aligned bubble with Maya avatar ("M"). Splits content on double newlines → one `<p>` per paragraph. Handles the combined intake + recommendation message (two paragraphs) gracefully.

`appendSystemMessage(content)` — centred grey error message.

`showTypingIndicator()` / `hideTypingIndicator()` — animated three-dot bubble. Guards against duplicates with an `getElementById` check.

`clearChat()` — `getThread().innerHTML = ""`. Called on new conversation.

All DOM writes use `textContent` or `createElement + appendChild`, never `innerHTML` with user-supplied content — prevents XSS.

---

### `frontend/src/decision.ts`

Manages the right-side decision panel (the internal-facing view, visible in Demo Mode).

`showPlaceholder()` — shows the "Waiting for recommendation..." placeholder.

`updateDecision(decision: DecisionData)` — renders all 8 fields:
- **Vertical badge** — colour-coded: purple (gifting), blue (loyalty), orange (brand_engagement), green (enterprise_rewards)
- **Intent badge** — grey (browsing), amber (engaged), green (high_intent)
- **Confidence bar** — animated from previous value to target using `requestAnimationFrame` + 50ms `setTimeout`. CSS `transition: width 0.6s ease` does the actual animation. `previousScore` is module-level so the bar animates from wherever it was last time.
- **Reasoning** — plain text
- **Next question chips** — `<button class="question-chip">` elements. Click calls `nextQuestionCallback(q)` registered by `main.ts`.

`addIntentDot(tier)` — appends a coloured dot to `#intent-timeline`. Builds a visual trail of intent signals across the conversation.

`onNextQuestionClick(callback)` — registers the callback. When a chip is clicked, `main.ts` pre-fills the input and calls `handleSend()` automatically.

---

### `frontend/src/main.ts`

The application entry point and orchestrator. Imports from all other modules.

**Mode switching:**
```typescript
function setMode(mode: AppMode): void {
  document.body.className = `mode-${mode}`;  // CSS handles all show/hide
  // ...activate correct nav button
  if (mode === "sales") refreshSessionsList();
}
```
The entire layout is controlled by CSS scoped to `body.mode-demo`, `body.mode-customer`, `body.mode-sales`. There is no other JS show/hide logic. Switching modes is one className change.

**`handleSend(messageText)`** — the core send flow:
1. `checkPricingKeywords()` + `incrementMessageCount()`
2. Render user bubble immediately (optimistic), clear input, show typing indicator, disable input
3. Build `ChatRequest` with conditional `session_id`
4. `await sendMessage(req)`
5. Success: hide indicator, `updateFromResponse()`, `appendAssistantMessage()`, if decision: `updateDecision()` + `addIntentDot()`, show summary button if conditions met
6. Error: hide indicator, `appendSystemMessage()`
7. Finally: `setSendingState(false)`, `getInput().focus()`

**`triggerGreeting()`** — sends `{message: "hi"}` 500ms after load. Starts the session and gets Maya's opening message without the user typing anything.

**`setupPresets()`** — creates 4 preset buttons dynamically from the `PRESETS` array. Each calls `handleSend(message)` directly.

**`refreshSessionsList()`** — fetches `GET /sessions`, renders one `.session-card` per session with vertical/intent badges and relative timestamps ("2m ago"). Clicking a card calls `loadSessionDetail()`.

**`loadSessionDetail(sessionId, card)`** — fetches the session summary, renders the full detail panel: session ID, phase, vertical + intent badges + confidence %, pain point box, profile table, raw quotes, CRM summary, intent progression dots, Push to CRM button.

**`showCrmToast(sessionId)`** — creates a slide-up toast at bottom-right. CSS transition: `translateY(20px); opacity: 0` → `.toast-visible` → `translateY(0); opacity: 1`. Auto-dismisses after 3.5 seconds.

**Bootstrap (`DOMContentLoaded`):** sets Demo mode, wires all button listeners, registers the chip click callback, fires `triggerGreeting` after 500ms.

---

### `frontend/index.html`

The single HTML file. Contains all CSS in a `<style>` block and all structural HTML. No external CSS framework — pure custom CSS.

**Layout structure:**
```
#mode-bar  (44px top bar, always visible)
  3x .mode-btn  [Demo] [Customer View] [Sales Dashboard]

#app  (calc(100vh - 44px), flex row)
  #left-wrapper
    .demo-label  ("Customer View" — only visible in Demo mode)
    #chat-panel
      #top-bar  (New Conversation button, summary button)
      #preset-row  (Gifting / Loyalty / Brand / Enterprise buttons)
      #chat-thread  (scrollable, grows to fill space)
      #input-row  (textarea + send button)

  #right-wrapper
    .demo-label  ("Internal Decision Panel" — only visible in Demo mode)
    #decision-panel
      #decision-placeholder  ("Waiting for first recommendation...")
      #decision-content
        (vertical badge, campaign card, confidence bar,
         intent badge + description, reasoning, chips, intent timeline)

  #sales-dashboard  (entirely separate section, replaces both above)
    #dashboard-top  (title, refresh button)
    #dashboard-body  (flex row)
      #sessions-sidebar  (scrollable list of session cards)
      #session-detail-panel  (selected session detail view)
```

**CSS mode rules:**
```css
/* Demo — split screen, labels visible */
body.mode-demo #left-wrapper   { display: flex; width: 60%; }
body.mode-demo #right-wrapper  { display: flex; width: 40%; }
body.mode-demo #sales-dashboard { display: none; }
body.mode-demo .demo-label     { display: block; }

/* Customer — chat only, no internal data */
body.mode-customer #left-wrapper   { width: 100%; border-right: none; }
body.mode-customer #right-wrapper  { display: none; }
body.mode-customer #sales-dashboard { display: none; }
body.mode-customer .demo-label     { display: none; }
body.mode-customer #preset-row     { display: none; }
body.mode-customer #top-bar-actions { display: none; }

/* Sales — dashboard replaces everything */
body.mode-sales #left-wrapper   { display: none; }
body.mode-sales #right-wrapper  { display: none; }
body.mode-sales #sales-dashboard { display: flex; }
body.mode-sales .demo-label     { display: none; }
```

Switching modes is one `className` change on `body` — CSS does everything declaratively.

**Key CSS patterns:**
- Dark theme: `--bg: #0a0a0a`, `--surface: #141414`, `--border: #1f1f1f`
- Confidence bar: `transition: width 0.6s ease` — JS sets the width, CSS animates it
- Typing dots: `@keyframes bounce` with staggered `animation-delay` per dot
- CRM toast: `transform: translateY(20px); opacity: 0` base → `.toast-visible` → `translateY(0); opacity: 1`; `transition: 0.3s ease`
- Mobile breakpoint at 768px: stacks layout vertically

---

## Test files

---

### `tests/test_intake.py`

Unit tests for `run_intake()`. Uses `unittest.mock.patch` to replace `httpx.AsyncClient` with `AsyncMock` — no real network calls, no API key needed. All tests are `@pytest.mark.asyncio`.

**Helper `_make_mistral_response(content)`** — creates a `MagicMock` that simulates the Mistral API response shape `{"choices": [{"message": {"content": content}}]}`.

**5 tests:**

1. `test_profile_not_complete_returns_chat_message` — LLM returns a question, no sentinel. Assert `profile_complete == False`, `chat_message == reply`, `profile_data == None`.

2. `test_profile_complete_detected_and_parsed` — LLM reply is `"chat text\nPROFILE_COMPLETE\n{json}"`. Assert `profile_complete == True`, all four fields parsed correctly.

3. `test_malformed_json_after_profile_complete_returns_recovery_message` — sentinel present, JSON garbled. Assert `profile_complete == False`, `profile_data == None`, non-empty recovery message.

4. `test_timeout_returns_friendly_message` — mock raises `httpx.TimeoutException`. Assert `profile_complete == False`, `chat_message` contains "again" or "sorry".

5. `test_conversation_history_is_included_in_messages` — captures the POST payload via a side-effect function. Assert the `messages` array contains system, user, and assistant roles in correct order, with the new user message last.

---

### `tests/test_recommendation.py`

Unit tests for `build_recommendation_prompt()`, `run_recommendation()`, and `run_followup()`.

**3 synchronous prompt tests:**

1. `test_build_recommendation_prompt_includes_profile` — pain_point and goal strings appear in the built prompt.
2. `test_build_recommendation_prompt_includes_product_knowledge` — unique sentinel string injected as knowledge appears verbatim.
3. `test_build_recommendation_prompt_includes_decision_sentinel` — `---DECISION---` appears in the prompt.

**5 async `run_recommendation()` tests:**

4. `test_decision_parsed_correctly_from_response` — inline sentinel path, valid JSON. Assert `vertical == "loyalty"`, `confidence_score ≈ 0.87`, `len(next_questions) == 3`.

5. `test_fallback_used_when_decision_json_is_malformed` — sentinel present, JSON invalid. Both LLM calls mocked (extraction call also fires). Assert `decision == _FALLBACK_DECISION`.

6. `test_fallback_used_when_sentinel_missing` — no sentinel at all. Assert `chat_message == reply`, `decision == _FALLBACK_DECISION`.

7. `test_missing_fields_patched_from_fallback` — valid JSON with only 2 of 8 fields. Assert the 2 provided fields preserved, the 6 missing fields filled from `_FALLBACK_DECISION`.

**1 async `run_followup()` test:**

8. `test_followup_returns_chat_message_only` — result has `chat_message` key, does NOT have `decision` key.

---

### `tests/test_e2e.py`

Integration tests against the real FastAPI server on `localhost:8000`. Real Mistral API calls. All tests use synchronous `httpx` — no async needed.

**Auto-skip mechanism:**
```python
def _server_running() -> bool:
    try:
        httpx.get(f"{BASE}/health", timeout=3.0)
        return True
    except Exception:
        return False

skip_if_offline = pytest.mark.skipif(not _server_running(), reason="...")
```
All tests decorated with `@skip_if_offline`. If the server is not up: SKIPPED (not FAILED). CI without a running server stays green.

`TIMEOUT = 60.0` — real Mistral API calls can take 5–15 seconds.

**5 tests:**

1. `test_health_endpoint` — `GET /health` returns 200, `{"status": "ok"}`.

2. `test_full_loyalty_conversation` — sends 4 real messages from the `TURNS` list. Asserts: stable `session_id` across all turns, final `phase == "recommendation"`, `is_complete == True`, decision present with all 8 required fields, valid `vertical`, `0.0 ≤ confidence_score ≤ 1.0`, valid `intent_tier`, non-empty `next_questions`.

3. `test_session_summary_after_conversation` — runs the 4-turn flow, fetches summary. Assert `total_turns == len(TURNS) * 2` (4 user + 4 assistant = 8), `phase == "recommendation"`, profile and intent_score_progression present.

4. `test_rate_limit_returns_429_after_30_rapid_requests` — fires 31 rapid requests on a fresh session (timestamp-based ID). Assert 429 appears in the status list.

5. `test_delete_session` — creates session, deletes it (`{"deleted": true}`), confirms 404 on summary.

---

## Infrastructure files

---

### `Dockerfile`

Multi-stage build. Stage 1 is Node 20-slim, stage 2 is Python 3.11-slim.

**Stage 1 (node-builder):** Installs npm dependencies, runs `npm run build` → produces `frontend/dist/bundle.js` and `frontend/dist/index.html`.

**Stage 2 (final):** Installs Python dependencies, copies only the compiled `dist/` from stage 1 (not Node, not `node_modules`), copies `app/`, runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

Result: one image, one port, zero external services, no Node runtime in the production image.

### `docker-compose.yml`

Single service. Maps host 8000 → container 8000. Reads `MISTRAL_API_KEY` from `.env`. `restart: unless-stopped`.

### `start.sh`

```bash
cd frontend && npm run build && cd .. && uvicorn app.main:app --reload --port 8000
```

Builds the frontend then starts the backend. `--reload` watches Python files. Frontend requires a manual rebuild on TypeScript changes.

### `requirements.txt`

Key dependencies:
- `fastapi` — web framework, routing, Pydantic integration, automatic OpenAPI at `/docs`
- `uvicorn[standard]` — ASGI server with `uvloop` (faster event loop) and `httptools` (faster HTTP parsing)
- `pydantic` — v2, data validation and serialisation
- `httpx` — async HTTP client for Mistral API calls. Using `requests` (synchronous) would block the FastAPI event loop — `httpx.AsyncClient` is essential here
- `python-dotenv` — loads `MISTRAL_API_KEY` from `.env` at startup
- `pytest` + `pytest-asyncio` — test runner with async support

---

## Key design decisions — interview talking points

**1. Two-LLM pipeline with a dedicated extraction micro-call**

Intake and recommendation are separate calls with different temperatures (0.7 vs 0.4) and different system prompts. Within recommendation, a third micro-call at temperature 0.1 handles JSON extraction when the primary call fails to produce valid structured output. This three-call pattern solves a real reliability problem observed during development: models optimised for natural conversation consistently omit structural markers or produce malformed JSON when asked to do both at once in a single response.

**2. Sentinel-based structured output protocol**

Instead of using Mistral's function-calling or JSON-mode APIs, the system instructs the LLM to write a plain-text sentinel (`PROFILE_COMPLETE`, `---DECISION---`) and then raw JSON. The backend splits on the sentinel. The benefit is transparency — you can read the raw LLM output and immediately understand what it produced. The cost is fragility when the LLM omits the sentinel, which the extraction fallback mitigates completely. The alternative (Mistral JSON mode) would be more reliable but less readable and harder to debug.

**3. In-memory session store with no infrastructure dependencies**

All session state lives in a Python module-level dict. Zero infrastructure requirements — just run `uvicorn`. The `session_store.py` module exposes clean function signatures so the storage layer is entirely swappable: replacing the dict with Redis calls means changing only that one file, not any agent or routing code.

**4. CSS-driven view modes, not JavaScript**

The three UI modes are controlled by one `className` on `document.body`. Every show/hide rule is declarative CSS. JavaScript changes exactly one thing. This makes the UI deterministic — there is no JS state that can diverge from what is visible. It is also instantly testable: load the HTML, add a class to body, inspect with DevTools.

**5. Sliding-window deque rate limiter with lazy eviction**

The rate limiter uses `collections.deque` per session. Expired timestamps are lazily evicted at the start of each request. No background process, no cron job, no memory leak — expired entries are cleaned up automatically on each incoming request. The deque is bounded in practice because the eviction runs before the count is checked.

**6. esbuild with strict TypeScript and no framework**

The 13.8 kb bundle is produced in ~6 ms. TypeScript `strict: true` and `exactOptionalPropertyTypes: true` catch real bugs at compile time (one manifested during development: assigning `undefined` to an optional field). No React or Vue means no virtual DOM, no hydration, no build complexity. For a focused tool with a fixed set of views, direct DOM manipulation is simpler, faster, and easier to reason about than a framework.

**7. Product knowledge as code, not a database**

The entire Gesture product catalogue is a Python dict. This is the simplest possible RAG implementation — retrieve everything, inject everything into the system prompt. It is readable, versionable in git, and testable. The trade-off is that it does not scale to hundreds of products without hitting context limits. The production upgrade path: chunk the knowledge base, embed with a sentence transformer, store in a vector DB, retrieve only the top-k chunks relevant to the detected vertical on each recommendation call.
