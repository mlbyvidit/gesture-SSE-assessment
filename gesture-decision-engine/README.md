# Gesture Decision Engine

An AI-powered sales qualification and recommendation tool built with FastAPI, Mistral Small, and a vanilla TypeScript frontend. A visitor chats with an AI persona (Maya), who collects their needs through conversation and delivers a tailored product recommendation — all in one session, no forms, no database required.

> Built as Part 2 (Option A) of the Gesture Senior Software Engineer assessment.

---

## What's in this repo

```
gesture-decision-engine/
├── app/                      Python backend (FastAPI)
├── frontend/                 TypeScript SPA (esbuild, no framework)
├── tests/                    Unit + e2e tests (pytest)
├── Dockerfile
├── docker-compose.yml
├── start.sh                  One-command local start
├── requirements.txt
├── PRODUCT_OVERVIEW.md       Full walkthrough of what the app does and why
└── ARCHITECTURE.md           Deep technical breakdown of every file
```

---

## Quick start (local, recommended)

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Node | 18+ |
| Mistral API key | Free at [console.mistral.ai](https://console.mistral.ai) |

### 1. Enter the project directory

```bash
cd gesture-decision-engine
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and set your key:

```
MISTRAL_API_KEY=your_key_here
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Build the frontend and start the server

```bash
./start.sh
```

This does two things in sequence: builds the TypeScript frontend into `frontend/dist/`, then starts the FastAPI server on port 8000 with hot-reload.

Open **http://localhost:8000** — Maya greets you automatically within half a second.

---

## Quick start (Docker)

If you'd rather not install Python or Node locally, Docker handles everything.

```bash
cp .env.example .env
# Edit .env — add your MISTRAL_API_KEY

docker-compose up --build
```

Open **http://localhost:8000**.

To stop: `docker-compose down`

---

## Using the app

The interface has three modes, toggled from the top bar:

| Mode | What you see |
|---|---|
| **Demo** | Split screen — chat on the left, live decision panel on the right |
| **Customer View** | Chat only — what a real end-user would see (no internal data) |
| **Sales Dashboard** | All active sessions — vertical, intent tier, full profile, CRM summary |

**To trigger a full recommendation quickly:** use one of the four preset buttons (Gifting, Loyalty, Brand, Enterprise) at the top of the chat. Each sends a realistic opening message and runs through to a recommendation in 2–3 turns.

---

## Running the tests

### Unit tests — no server needed, runs in ~0.1s

```bash
python -m pytest tests/test_intake.py tests/test_recommendation.py -v
```

Tests 13 things: profile detection, JSON parsing, fallback handling, timeout recovery, prompt construction, decision extraction, and follow-up behaviour. All use mocked HTTP — no Mistral API key needed.

### End-to-end tests — requires a running server

Start the server first (`./start.sh`), then:

```bash
python -m pytest tests/test_e2e.py -v
```

Covers: full 4-turn loyalty conversation, session summary, rate limiting (429), missing session (404), session deletion. Auto-skipped if the server is not reachable — they will not fail CI.

---

## API at a glance

| Method | Path | What it does |
|---|---|---|
| `POST` | `/chat` | Send a message — handles intake and follow-up in the same route |
| `GET` | `/session/{id}/summary` | Full session profile + CRM note (Mistral-generated) |
| `GET` | `/sessions` | All active sessions — used by the Sales Dashboard |
| `DELETE` | `/session/{id}` | Remove a session from memory |
| `GET` | `/health` | `{"status": "ok"}` |

Minimal `POST /chat` example:

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "we have 50000 loyalty members and redemption rates are low"}'
```

Response includes `session_id` — pass it back on every subsequent message to maintain the conversation.

---

## Further reading

- **[PRODUCT_OVERVIEW.md](./PRODUCT_OVERVIEW.md)** — full walkthrough of what the app does, how the conversation works, what the decision panel shows, and what a production version would look like
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — technical deep-dive into every file, design decisions, and the two-LLM pipeline
