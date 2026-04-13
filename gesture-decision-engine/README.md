# Gesture Decision Engine

A full-stack AI application that qualifies inbound interest for Gesture's platform through a two-phase conversation, then delivers a structured product recommendation with intent scoring — powered by Mistral Small and served as a single FastAPI application with a TypeScript frontend.

---

## Table of Contents

1. [What this application does](#1-what-this-application-does)
2. [How to use it — user walkthrough](#2-how-to-use-it--user-walkthrough)
3. [How it works — under the hood](#3-how-it-works--under-the-hood)
4. [The two-LLM architecture](#4-the-two-llm-architecture)
5. [The decision panel explained](#5-the-decision-panel-explained)
6. [The session and state system](#6-the-session-and-state-system)
7. [The product knowledge base](#7-the-product-knowledge-base)
8. [The intent scoring system](#8-the-intent-scoring-system)
9. [The API](#9-the-api)
10. [Project structure](#10-project-structure)
11. [Setup and running locally](#11-setup-and-running-locally)
12. [Running with Docker](#12-running-with-docker)
13. [Running the tests](#13-running-the-tests)
14. [What comes next](#14-what-comes-next)

---

## 1. What this application does

The Gesture Decision Engine is an AI-powered qualification and recommendation tool. It does three things:

**Qualifies leads through conversation.** A user opens the app and starts chatting with Maya, an AI intake specialist. Maya asks a small number of focused questions to understand who the user is, what they are trying to achieve, how big their audience is, and how urgently they want to move. The user never fills in a form — they just have a natural conversation.

**Makes a specific product recommendation.** Once Maya has enough information, the system automatically switches to a second AI agent that has full knowledge of Gesture's product catalogue. This agent gives a detailed, priced, and timed recommendation based on the user's exact situation — referencing their specific pain point, scale, and timeline.

**Produces structured, CRM-ready output.** Every conversation ends with a structured data object that captures the vertical, recommended campaign, confidence score, intent tier, reasoning, and suggested follow-up questions. There is also a session summary endpoint that generates a single-sentence CRM note describing the lead.

---

## 2. How to use it — user walkthrough

### Opening the app

When you open `http://localhost:8000`, the app loads a split-screen interface. The left side is the chat. The right side is the decision panel. Within half a second, Maya sends a greeting automatically — you do not need to type anything first.

```
Maya: Hey there! What brings you to Gesture today?
```

### Having the intake conversation

Just describe your situation naturally. Maya will ask one focused question at a time to build your profile. You do not need to answer in a specific format — she understands conversational language.

Example exchange:

```
You:  We have about 50,000 loyalty members and churn is getting worse every quarter.

Maya: I'm sorry to hear that — high churn is a tough problem. Are these loyalty
      members your direct customers, or employees, or partners?

You:  Customers. We're a retail brand. We have a points programme but nobody
      actually redeems the points.

Maya: Got it — low redemption on an existing points programme is exactly the
      kind of pain we solve for. How urgently are you looking to move?
      Are you thinking about launching something in Q1, or still in
      the exploration phase?

You:  We want to move fast — Q1 is the target.

Maya: Perfect, I have everything I need. I'm pulling together your
      recommendation now...
```

Maya needs four pieces of information before she will switch to the recommendation phase:

| Field | What she is collecting | Example values |
|---|---|---|
| Audience | Who the programme targets | customers, employees, partners, brand |
| Scale | How many people | small (<500), medium (hundreds), large (thousands), enterprise (50k+) |
| Goal | What outcome is needed | retention, recognition, engagement, acquisition |
| Timeline | How urgently | immediate (Q1/now), planned (next quarter), exploring |

She also picks up bonus context if it comes up naturally: whether you have an existing programme, your exact pain point in your own words, and what type of company you are.

### Receiving the recommendation

Once Maya has the four required fields, the system automatically triggers a second AI call with full product knowledge. The recommendation appears in the same chat thread, seamlessly continuing as Maya:

```
Maya: Based on your situation — 50,000 loyalty members with low redemption
      rates and high churn — I'd recommend our Loyalty vertical, specifically
      the Points-to-Gift product. This lets your customers redeem their
      existing points for curated physical gifts they actually want, which
      directly addresses your "nobody redeems points" pain point.

      For a programme of your scale, pricing starts at $2,000/month plus
      per-gift cost, and we can integrate with your existing loyalty platform
      in 3–4 weeks — well within your Q1 timeline. Clients like yours have
      seen redemption rates jump from under 20% to over 85%, and churn drop
      by 25–40% in gifted segments within 90 days.

      Would you like to see a quick ROI projection based on your current
      churn numbers?
```

At the same moment, the right-side decision panel updates with the structured output.

### Using the decision panel

The right panel shows five things once a recommendation is made:

- **Vertical badge** — colour-coded tag showing which of Gesture's four verticals was matched (Gifting, Loyalty, Brand Engagement, Enterprise Rewards)
- **Recommended campaign** — the specific product name and a one-line description of what it does
- **Confidence score** — an animated progress bar showing how confident the system is in its recommendation (0–100%)
- **Intent tier** — a badge showing whether the prospect is Browsing, Engaged, or High Intent, with a one-sentence description
- **Suggested next questions** — three clickable chips. Click any chip and it populates the input field and sends automatically, continuing the conversation.

### Using the demo presets

Four preset buttons appear at the top of the chat panel, one per vertical. Clicking a preset populates a realistic scenario message and sends it immediately. This is the fastest way to see each vertical in action:

| Preset | Message sent |
|---|---|
| Gifting | "I want to send personalised holiday gifts to my top 200 customers" |
| Loyalty | "We have 50,000 loyalty members and redemption rates are really low" |
| Brand | "We are launching a new product and want an experiential activation" |
| Enterprise | "I need to reward our sales team at end of Q4 with something memorable" |

### Starting a new conversation

Click "New Conversation" in the top-right to reset the session, clear the chat, and trigger Maya's greeting again. The decision panel returns to its placeholder state.

### Viewing the session summary

After a recommendation has been made, a "View Summary" button appears in the top bar. Clicking it opens a modal with the full session summary including the complete user profile, intent score progression across turns, and a one-sentence CRM note generated by the AI.

---

## 3. How it works — under the hood

Every message you send goes through this sequence:

```
Browser sends POST /chat
         │
         ▼
main.py receives ChatRequest
         │
         ├─ Resolve or create session (UUID)
         ├─ Check rate limit (30 req/min per session)
         ├─ Store user message in session history
         ├─ Compute intent score for this message
         │
         ▼
Is session.phase == "intake"?
         │
    YES  │                          NO (phase == "recommendation")
         ▼                                    ▼
   run_intake()                         run_followup()
   (LLM Call 1)                         (LLM Call 2b)
         │
         ▼
  profile_complete == True?
         │
    YES  │
         ▼
   update_profile()
   set_phase("recommendation")
         │
         ▼
   run_recommendation()
   (LLM Call 2a — chat)
         │
         ▼
   _extract_decision_json()
   (LLM Call 2b — JSON)
         │
         ▼
   return ChatResponse with
   decision populated
```

All session data is held in memory (a Python dict). No database is required for the prototype.

---

## 4. The two-LLM architecture

The system makes two separate LLM calls with completely different roles. This is a deliberate architectural decision, not a convenience.

### LLM 1 — The Intake Agent (`app/intake_agent.py`)

| Property | Value |
|---|---|
| Model | `mistral-small-latest` |
| Temperature | 0.7 (warmer, more conversational) |
| Max tokens | 400 |
| System prompt | Intake only — no product knowledge |
| Persona | Maya, intake specialist |

The intake agent knows nothing about Gesture's products, pricing, or campaigns. This is intentional. Keeping the intake agent product-blind means it cannot hallucinate recommendations prematurely, cannot get sidetracked into a product pitch before it has enough context, and stays genuinely focused on the user's situation.

The intake agent's only job is to collect four fields and then emit a structured signal. When it has enough information, it writes a warm closing message and then appends a sentinel token `PROFILE_COMPLETE` followed by a raw JSON object containing the collected profile. The backend detects this sentinel, parses the JSON, stores it as the session's `UserProfile`, and transitions the session to the recommendation phase.

### LLM 2 — The Recommendation Agent (`app/recommendation_agent.py`)

| Property | Value |
|---|---|
| Model | `mistral-small-latest` |
| Temperature | 0.4 (cooler, more precise and factual) |
| Max tokens | 1000 (chat) + 500 (JSON extraction) |
| System prompt | Full product knowledge + validated profile |
| Persona | Maya, senior product expert |

The recommendation agent receives two things it never had during intake: the complete, validated user profile as structured JSON, and the entire Gesture product knowledge base including all four verticals, specific product names, real pricing, typical results, and time-to-launch figures.

Because the model (Mistral Small) reliably generates great conversational text but sometimes omits structured JSON sentinels, the recommendation phase uses **two sequential calls**:

- **Call 2a** — generate the conversational recommendation (warm, specific, priced)
- **Call 2b** — extract structured decision JSON from the recommendation text (`temperature: 0.1`)

This separation means the chat response is never held up waiting for JSON to parse correctly, and the JSON extraction has a clean, focused job with minimal chance of error.

### Why the same persona (Maya) for both agents

The user experiences a single continuous conversation. The switch from intake to recommendation is invisible — Maya is the same warm voice throughout. The difference is that after the intake phase she goes from curious-and-collecting to knowledgeable-and-advising. Users often say the recommendation feels like talking to someone who has done their homework, because the second agent literally receives a structured briefing before answering.

---

## 5. The decision panel explained

The right panel renders the `DecisionData` object returned by the recommendation agent. Each field maps to a visible element:

| Field | What it means | How it is shown |
|---|---|---|
| `vertical` | Which of Gesture's four product lines fits best | Colour-coded badge (purple=gifting, blue=loyalty, orange=brand, green=enterprise) |
| `vertical_description` | One sentence on why this vertical fits the prospect | Text below the badge |
| `recommended_campaign` | Specific product name and what it does | Card with bold product name |
| `confidence_score` | 0.0–1.0 float from the LLM | Animated progress bar, percentage label |
| `intent_tier` | browsing / engaged / high_intent | Colour-coded badge (grey / amber / green) |
| `intent_description` | One sentence on where the prospect is in their buying journey | Text below the intent badge |
| `reasoning` | Two sentences citing specific signals from the profile | Quoted block with left border |
| `next_questions` | Three follow-up questions to advance the conversation | Clickable chip buttons |

The confidence bar animates from its previous value to the new value on each update — this makes it visually obvious when the score changes across turns.

The intent journey timeline at the bottom of the panel adds a coloured dot on each turn, building a visual trail of how intent has changed across the conversation.

---

## 6. The session and state system

Every conversation is a session. A session is created automatically on the first message and lives in memory for the lifetime of the server process.

### Session lifecycle

```
First message (no session_id) → create_session() → returns UUID
All subsequent messages → pass session_id in request body → get_session()
Recommendation made → set_phase("recommendation")
User clicks New Conversation → DELETE /session/{id} (optional) + new session on next message
```

### What is stored per session

```python
SessionData:
  session_id: str               # UUID
  phase: str                    # "intake" or "recommendation"
  messages: list[dict]          # full conversation history sent to LLM on each call
  profile: UserProfile          # structured fields collected during intake
  created_at: float             # unix timestamp
  last_updated: float           # updated on every message
  intent_score_history: list    # score computed per turn
```

### Rate limiting

Each session is limited to 30 requests per 60 seconds. This is enforced via a sliding-window deque of timestamps per session ID. Exceeding the limit returns HTTP 429. The rate limiter does not count rejected requests against the window.

---

## 7. The product knowledge base

The file `app/product_knowledge.py` contains everything the recommendation agent knows about Gesture. It is a Python dict called `PRODUCT_KNOWLEDGE` that is serialised to JSON and injected into the recommendation agent's system prompt on every call.

The knowledge base covers:

- **Company overview** — what Gesture is and what it does
- **Four verticals**, each with: description, specific product names, pricing details, ideal customer profile, typical results, and time-to-launch
- **How it works** — the five-step platform flow (Connect → Curate → Choose → Deliver → Measure)
- **Integrations** — Salesforce, HubSpot, Shopify, Custom API
- **Differentiators** — recipient choice, white-label experience, global fulfilment, real measurement, zero inventory risk
- **Common objections** — five pre-written responses to "too expensive", "we already have swag", logistics concerns, integration concerns, and scale concerns
- **Pilot programme** — 90-day pilot terms

The four verticals are:

| Vertical | Who it is for | Core products |
|---|---|---|
| **Gifting** | D2C brands, subscription companies, e-commerce | Gift Finder, Occasion Engine, Gift-with-Purchase |
| **Loyalty** | Retail, hospitality, subscription boxes | Points-to-Gift, VIP Early Access Box, Re-engagement Kit |
| **Brand Engagement** | CPG, fashion, tech (launches and campaigns) | Launch Kit, Pop-up Experience Box, Community Appreciation Drop |
| **Enterprise Rewards** | Mid-market and enterprise HR and sales teams | Milestone Recognition, Sales Performance Reward, Executive Gifting |

The recommendation agent uses this knowledge base to cite real prices, real timelines, and real results in its response. The intake agent never sees this file.

---

## 8. The intent scoring system

Every message is scored for purchase intent before being passed to the LLM. The score is a float between 0.0 and 1.0 and is stored in the session's `intent_score_history` list.

### How the score is computed

```
score = 0.0

If the message contains a high-intent keyword:    +0.25
  (pricing, price, cost, budget, how much, ready, start,
   contract, timeline, pilot, integrate, asap, urgent,
   next steps, sign up)

If the message contains a mid-intent keyword:     +0.12
  (interested, considering, demo, example, tell me more,
   how does, what is, case study)

If the session has more than 4 messages so far:   +0.15
  (signals engagement depth)

If the session has more than 8 messages so far:   +0.10
  (signals high engagement depth)

score = min(score, 1.0)
```

### How the score maps to a tier

| Score | Tier | Meaning |
|---|---|---|
| 0.00 – 0.34 | `browsing` | Early stage, no urgency signals |
| 0.35 – 0.64 | `engaged` | Showing interest, worth nurturing |
| 0.65 – 1.00 | `high_intent` | Active buying signals, route to AE |

The tier from the scoring system is passed to the recommendation agent as a fallback. The LLM also produces its own `intent_tier` based on reading the conversation, which typically overrides the keyword score for the displayed value.

---

## 9. The API

The server exposes four endpoints. All are served at `http://localhost:8000`.

### `POST /chat`

The main endpoint. Handles both intake and post-recommendation follow-up in the same route.

**Request:**
```json
{
  "message": "we have 50000 loyalty members and churn is high",
  "session_id": "optional — omit on first message, include on all subsequent"
}
```

**Response during intake:**
```json
{
  "chat_message": "Thanks for sharing that. Are these customers, employees, or partners?",
  "session_id": "35ff40f4-066b-41ed-94b2-8f741f4c30b9",
  "phase": "intake",
  "is_complete": false,
  "decision": null
}
```

**Response when recommendation fires:**
```json
{
  "chat_message": "Based on your situation... [full recommendation]",
  "session_id": "35ff40f4-066b-41ed-94b2-8f741f4c30b9",
  "phase": "recommendation",
  "is_complete": true,
  "decision": {
    "vertical": "loyalty",
    "vertical_description": "Tangible rewards that make loyalty programmes feel real and valuable.",
    "recommended_campaign": "Points-to-Gift — customers redeem existing points for curated physical gifts",
    "confidence_score": 0.95,
    "intent_tier": "high_intent",
    "intent_description": "Prospect has a clear pain point, existing programme, and an immediate Q1 deadline.",
    "reasoning": "50,000 loyalty members with sub-20% redemption rates is the exact problem Points-to-Gift solves. The Q1 timeline is achievable with a 3-4 week integration.",
    "next_questions": [
      "What platform manages your loyalty points today?",
      "Do you have a target gift budget per member?",
      "Would a 90-day pilot with no long-term commitment work for your Q1 timeline?"
    ]
  }
}
```

**Error responses:**
- `422` — message is empty or exceeds 1000 characters
- `429` — rate limit exceeded (30 requests per minute per session)

---

### `GET /session/{session_id}/summary`

Returns a full structured summary of the session. Intended to be the payload sent to a CRM system.

**Response:**
```json
{
  "session_id": "35ff40f4-066b-41ed-94b2-8f741f4c30b9",
  "total_turns": 8,
  "phase": "recommendation",
  "profile": {
    "audience": "customers",
    "scale": "enterprise",
    "goal": "retention",
    "timeline": "immediate",
    "existing_program": true,
    "pain_point": "nobody redeems our points",
    "company_type": "retail brand",
    "raw_quotes": [
      "we have 50000 loyalty members and churn is high",
      "we have a points programme but nobody redeems them"
    ],
    "is_complete": true
  },
  "final_intent_tier": "high_intent",
  "intent_score_progression": [0.0, 0.0, 0.15, 0.40],
  "top_vertical": null,
  "crm_summary": "Enterprise retail brand with 50K loyalty members seeking to fix sub-20% redemption rates and high churn — immediate Q1 timeline, existing points programme, high intent."
}
```

The `crm_summary` field is generated by a separate Mistral API call and is a single sentence suitable for pasting into a Salesforce or HubSpot lead record.

---

### `DELETE /session/{session_id}`

Removes the session from memory. Useful for cleaning up after a conversation or in tests.

**Response:** `{"deleted": true}`

---

### `GET /health`

Liveness check for load balancers and monitoring.

**Response:** `{"status": "ok", "version": "1.0.0"}`

---

## 10. Project structure

```
gesture-decision-engine/
│
├── app/                          Python backend
│   ├── main.py                   FastAPI app — all routes, intent scoring, phase logic
│   ├── models.py                 Pydantic models for all request/response types
│   ├── intake_agent.py           LLM 1 — Maya intake persona, profile collection
│   ├── recommendation_agent.py   LLM 2 — Maya product expert, recommendation + JSON extraction
│   ├── product_knowledge.py      Complete Gesture knowledge base (static dict)
│   ├── session_store.py          In-memory session CRUD + sliding-window rate limiter
│   └── __init__.py
│
├── frontend/
│   ├── src/
│   │   ├── main.ts               Entry point — wires all modules, handles send flow
│   │   ├── api.ts                fetch wrappers for /chat and /session/summary
│   │   ├── chat.ts               DOM functions — user/assistant bubbles, typing indicator
│   │   ├── decision.ts           Decision panel — vertical badge, score bar, chips
│   │   ├── session.ts            In-memory session state, intent tracking, reset
│   │   └── types.ts              TypeScript interfaces mirroring Pydantic models
│   ├── index.html                Full HTML with embedded CSS — dark/white split layout
│   ├── package.json              npm scripts: build (minified) and dev (watch)
│   └── tsconfig.json             Strict ES2020 TypeScript config
│
├── tests/
│   ├── test_intake.py            5 unit tests — mocked httpx, intake agent logic
│   ├── test_recommendation.py    8 unit tests — prompt construction, decision parsing
│   ├── test_e2e.py               5 integration tests — full flow against live server
│   └── __init__.py
│
├── .env.example                  API key template
├── .gitignore
├── requirements.txt              Pinned Python dependencies
├── start.sh                      One-command local start (builds frontend + starts uvicorn)
├── Dockerfile                    Multi-stage: Node 20 + Python 3.11 slim
├── docker-compose.yml            Single-service compose
└── README.md
```

---

## 11. Setup and running locally

### Prerequisites

- Python 3.11 or higher
- Node 18 or higher
- A Mistral API key — get one free at [console.mistral.ai](https://console.mistral.ai)

### Step 1 — Clone and enter the project

```bash
cd gesture-decision-engine
```

### Step 2 — Set your API key

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder with your real key:

```
MISTRAL_API_KEY=your_key_here
```

### Step 3 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Build the frontend and start the server

```bash
./start.sh
```

This script builds the TypeScript frontend into `frontend/dist/`, then starts uvicorn with hot-reload. Both steps happen in one command.

Open **http://localhost:8000** in your browser.

### Running backend and frontend separately (development)

If you want the frontend to rebuild automatically as you edit TypeScript:

```bash
# Terminal 1 — backend with hot reload
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend with watch mode
cd frontend && npm run dev
```

Changes to TypeScript files rebuild the bundle immediately. Refresh the browser to see updates.

---

## 12. Running with Docker

Docker handles everything — Node, Python, the build, and the server — in a single container.

```bash
# Make sure .env exists with your key first
cp .env.example .env
# Edit .env to add your real MISTRAL_API_KEY

# Build and start
docker-compose up --build

# Or run in the background
docker-compose up -d --build
```

Open **http://localhost:8000**.

To stop: `docker-compose down`

---

## 13. Running the tests

### Unit tests (no server required)

These test the intake and recommendation agents with mocked HTTP calls. They run in under a second.

```bash
python -m pytest tests/test_intake.py tests/test_recommendation.py -v
```

Expected output:

```
tests/test_intake.py::test_profile_not_complete_returns_chat_message PASSED
tests/test_intake.py::test_profile_complete_detected_and_parsed PASSED
tests/test_intake.py::test_malformed_json_after_profile_complete_returns_recovery_message PASSED
tests/test_intake.py::test_timeout_returns_friendly_message PASSED
tests/test_intake.py::test_conversation_history_is_included_in_messages PASSED
tests/test_recommendation.py::test_build_recommendation_prompt_includes_profile PASSED
tests/test_recommendation.py::test_build_recommendation_prompt_includes_product_knowledge PASSED
tests/test_recommendation.py::test_build_recommendation_prompt_includes_decision_sentinel PASSED
tests/test_recommendation.py::test_decision_parsed_correctly_from_response PASSED
tests/test_recommendation.py::test_fallback_used_when_decision_json_is_malformed PASSED
tests/test_recommendation.py::test_fallback_used_when_sentinel_missing PASSED
tests/test_recommendation.py::test_missing_fields_patched_from_fallback PASSED
tests/test_recommendation.py::test_followup_returns_chat_message_only PASSED

13 passed in 0.10s
```

### End-to-end tests (server must be running)

These tests call the real server with real Mistral API calls. Start the server first, then run:

```bash
python -m pytest tests/test_e2e.py -v
```

The e2e tests cover: full 4-turn loyalty conversation, session summary, rate limiting (429), missing session 404, and session deletion.

If the server is not running, all e2e tests are skipped automatically — they will not fail your CI.

---

## 14. What comes next

These are the production upgrades in order of impact:

**RAG over the product knowledge base.** The current implementation injects the full `PRODUCT_KNOWLEDGE` dict into every recommendation prompt. In production this should be replaced with a vector store (Pinecone or Vertex AI Matching Engine). The recommendation agent would retrieve only the top-k most relevant chunks — the right vertical's products, the objection handler that matches the user's concern — instead of everything. This reduces token cost and improves precision.

**Trained intent model.** The current intent score is keyword-based. It should be replaced with an XGBoost classifier trained on historical session data with CRM conversion outcomes as labels. Features would include message velocity, pricing keyword frequency, session depth, profile completion rate, and vertical keyword density. This produces a calibrated probability rather than a heuristic sum.

**CRM write-back via Pub/Sub.** When `intent_tier == "high_intent"` and a recommendation has been made, the session summary payload should be published to a Google Cloud Pub/Sub topic. A subscriber service writes the structured profile and CRM note to Salesforce or HubSpot as a new lead, tagged with the vertical, score, and source. This closes the loop to the sales team without any manual handoff.

**Redis session store.** The in-memory `_sessions` dict means all sessions are lost on server restart and the app cannot scale horizontally. Replacing it with Redis gives persistence, TTL-based expiry, and the ability to run multiple server instances behind a load balancer.

**A/B testing on intake prompts.** The intake system prompt is a single static string. It should be replaced with a pool of prompt variants that are randomly assigned per session. The variant used, the profile completion rate, the intent tier at completion, and the downstream conversion outcome are logged per session. The experimentation framework from Part 1 selects the winning variant and promotes it automatically once statistical significance is reached.

**Streaming responses.** Both LLM calls currently wait for the full response before returning. FastAPI supports `StreamingResponse` and Mistral supports streaming via SSE. Streaming the recommendation token by token would make the response feel significantly faster and more alive, especially for the longer recommendation messages.
