# Gesture Decision Engine

An AI-powered sales qualification and recommendation tool built with FastAPI, Mistral Small, and a vanilla TypeScript frontend. A visitor chats with an AI persona (Maya), who collects their needs through conversation and delivers a tailored product recommendation — all in one session, no forms, no database required.

> Built as Part 2 (Option A) of the Gesture Senior Software Engineer assessment.

---

## Live Demo

**The app is deployed and ready to use — no setup required:**

### https://gesture-sse-assessment.onrender.com

Just open the link and start chatting with Maya. No API key, no installation, nothing to configure.

> **Note:** It's hosted on Render's free tier, so if nobody has used it for a while it may take **30–50 seconds** to wake up on the first request. After that it's fast. If Maya doesn't respond immediately, just wait a moment and try again.

---

## Using the app

The interface has three modes, toggled from the top bar:

| Mode | What you see |
|---|---|
| **Demo** | Split screen — chat on the left, live decision panel on the right |
| **Customer View** | Chat only — what a real end-user would see (no internal data) |
| **Sales Dashboard** | All active sessions — vertical, intent tier, full profile, CRM summary |

**To see a full recommendation in 2–3 messages:** click one of the four preset buttons (Gifting, Loyalty, Brand, Enterprise) at the top of the chat. Each sends a realistic opening message and Maya will have enough context to recommend within a couple of turns.

---

## Running locally

If you want to run the code yourself — for example to explore it, run the tests, or make changes — follow one of the two options below. You'll need your own Mistral API key (free at [console.mistral.ai](https://console.mistral.ai)).

---

### Option A — Python + Node (recommended for development)

**Prerequisites:** Python 3.11+, Node 18+

```bash
# 1. Clone the repo
git clone https://github.com/mlbyvidit/gesture-SSE-assessment.git
cd gesture-SSE-assessment/gesture-decision-engine

# 2. Add your API key
cp .env.example .env
# Open .env and set: MISTRAL_API_KEY=your_key_here

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Build frontend and start server
./start.sh
```

Open **http://localhost:8000**

---

### Option B — Docker (no Python or Node needed)

**Prerequisites:** Docker Desktop

```bash
# 1. Clone the repo
git clone https://github.com/mlbyvidit/gesture-SSE-assessment.git
cd gesture-SSE-assessment/gesture-decision-engine

# 2. Add your API key
cp .env.example .env
# Open .env and set: MISTRAL_API_KEY=your_key_here

# 3. Build and run
docker-compose up --build
```

Open **http://localhost:8000**

To stop: `docker-compose down`

---

## Running the tests

```bash
# Unit tests — no server needed, no API key needed, runs in ~0.1s
python -m pytest tests/test_intake.py tests/test_recommendation.py -v

# End-to-end tests — start the server first, then run
python -m pytest tests/test_e2e.py -v
```

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

## API at a glance

| Method | Path | What it does |
|---|---|---|
| `POST` | `/chat` | Send a message — handles intake and follow-up in the same route |
| `GET` | `/session/{id}/summary` | Full session profile + CRM note (Mistral-generated) |
| `GET` | `/sessions` | All active sessions — used by the Sales Dashboard |
| `DELETE` | `/session/{id}` | Remove a session from memory |
| `GET` | `/health` | `{"status": "ok"}` |

---

## Further reading

- **[PRODUCT_OVERVIEW.md](./PRODUCT_OVERVIEW.md)** — full walkthrough of what the app does, how the conversation works, what the decision panel shows, and what a production version would look like
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — technical deep-dive into every file, design decisions, and the two-LLM pipeline
