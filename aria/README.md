# Aria — AI Voice Receptionist for Dental Clinics

> **Production-grade AI voice agent** | Day 14-16 of the AI Automation Engineer Journey

**Built by:** Lokesh Gaddam | [GitHub](https://github.com/LokeshGaddam14/ai-automation-engineer-journey)

---

## What is Aria?

Aria is an AI-powered voice receptionist for dental clinics that:

- 📞 **Handles real-time voice calls** via Bolna AI (Indian phone numbers)
- 📅 **Books appointments** on Google Calendar (prevents double-booking)
- 📱 **Sends confirmations** via WhatsApp + SMS through Twilio
- 🧠 **Remembers context** via Redis (during call) + PostgreSQL (forever)
- 🤖 **Routes intelligently** using LangGraph multi-agent architecture
- 🌍 **Speaks multiple languages**: English, Telugu, Hindi, Tamil

---

## Architecture

```
Patient Call (Bolna)
      ↓
┌─────────────────────────────────────┐
│   FastAPI /calls/start              │
│   → UnifiedCallHandler.start_call() │
└─────────────────────────────────────┘
      ↓
┌─────────────────────────────────────┐
│  1. Redis → Create session          │
│  2. Postgres → Check history        │
│  3. LangGraph → Route to agent      │
└─────────────────────────────────────┘
      ↓
┌─────────────────────────────────────┐
│  LangGraph State Machine            │
│  START → Greeting                   │
│       → Booking | Info | Emergency  │
│       → (Escalation if needed)      │
│       → END                         │
└─────────────────────────────────────┘
      ↓
┌─────────────────────────────────────┐
│  FastAPI /calls/end                 │
│  → Archive Redis → Postgres         │
│  → Twilio WhatsApp confirmation     │
└─────────────────────────────────────┘
```

---

## Quick Start

### 1. Setup

```bash
# From ai-automation root
cd ai-automation
cp aria/.env.example aria/.env
# Edit aria/.env with your credentials (optional — system runs in mock mode)
```

### 2. Install Dependencies

```bash
pip install -r aria/requirements.txt
```

### 3. Run Example Demo

```bash
python aria/examples/sample_call.py
```

### 4. Run Tests

```bash
pytest aria/tests/ -v
```

### 5. Start API Server

```bash
# Development (with auto-reload)
uvicorn aria.main:app --reload --port 8000

# Or via Python
python aria/main.py
```

### 6. Start Full Docker Stack (Production)

```bash
cd aria
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

---

## Project Structure

```
aria/
├── __init__.py                    ← Package root
├── main.py                        ← FastAPI application (20+ endpoints)
├── requirements.txt               ← Python dependencies
├── Dockerfile                     ← Container image
├── docker-compose.yml             ← Full stack (Redis + Postgres + API)
├── .env.example                   ← Configuration template
│
├── memory/                        ← Day 14: Two-tier memory
│   ├── __init__.py
│   ├── redis_manager.py           ← Real-time session state
│   └── postgres_manager.py        ← Durable archival
│
├── integrations/                  ← Day 15: External services
│   ├── __init__.py
│   ├── google_calendar.py         ← Appointment scheduling
│   └── twilio_client.py           ← WhatsApp + SMS notifications
│
├── agents/                        ← Day 15: Multi-agent system
│   ├── __init__.py
│   ├── orchestrator.py            ← LangGraph state machine
│   └── call_handler.py            ← Unified lifecycle manager
│
├── examples/
│   └── sample_call.py             ← Full flow demo
│
└── tests/
    └── test_aria.py               ← 20+ test cases
```

---

## API Endpoints

### Calls
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/calls/start` | Start incoming call |
| `POST` | `/calls/input` | Process patient speech |
| `POST` | `/calls/end` | End call + archive |
| `GET`  | `/calls/{call_id}` | Get call status |
| `GET`  | `/calls/{call_id}/transcript` | Full transcript |

### Patients
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/patients/{phone}` | Get patient info |
| `GET`  | `/patients/{phone}/history` | Call history |

### Bookings
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/bookings/remind` | Send reminder |
| `POST` | `/bookings/reschedule` | Reschedule |
| `POST` | `/bookings/cancel` | Cancel |
| `GET`  | `/bookings/pending` | Confirmed bookings |

### Calendar
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/calendar/slots` | Available slots |
| `GET`  | `/calendar/today` | Today's schedule |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/analytics/stats` | Call statistics |
| `GET`  | `/analytics/search` | Search calls |

### WebSocket
| Protocol | Endpoint | Description |
|----------|----------|-------------|
| `WS` | `/ws/call/{call_id}` | Real-time call handling |

**Full docs:** http://localhost:8000/docs (Swagger UI)

---

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `UPSTASH_REDIS_REST_URL` | Optional | Cloud Redis (upstash.com) |
| `DATABASE_URL` | Optional | Postgres/SQLite (defaults to SQLite) |
| `TWILIO_ACCOUNT_SID` | Optional | SMS/WhatsApp notifications |
| `TWILIO_AUTH_TOKEN` | Optional | Twilio secret |
| `GOOGLE_CALENDAR_ID` | Optional | Clinic calendar |
| `OPENAI_API_KEY` | Optional | LLM (uses Groq if not set) |
| `GROQ_API_KEY` | Optional | Free LLM API (groq.com) |

> **All services have mock/fallback modes** — the system works without any credentials for testing.

---

## Deployment

### Railway (Recommended — Free)
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Docker Production
```bash
cd aria
docker-compose build
docker-compose up -d
docker-compose logs -f aria-api
```

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for full deployment instructions.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Voice | Bolna AI (Indian phone support) |
| API | FastAPI + WebSocket |
| Agents | LangGraph (multi-agent state machine) |
| Session | Redis (Upstash cloud or local) |
| Storage | PostgreSQL (Supabase) or SQLite |
| Calendar | Google Calendar API |
| Notifications | Twilio (WhatsApp + SMS) |
| Container | Docker + Docker Compose |
| Tests | pytest (20+ test cases) |

---

## Interview Talking Points

**Architecture:**
> "I built a two-tier memory system: Redis for real-time session state (sub-millisecond latency) and PostgreSQL for durable archival. If the server restarts, Postgres has everything."

**Agent Routing:**
> "LangGraph routes between specialized nodes: GreetingAgent → BookingAgent → InfoAgent or EscalationAgent. Each turn, it decides the next action based on conversation context — like a state machine but with complex AI state."

**Scalability:**
> "FastAPI is async, so one instance handles 10k+ concurrent connections. Redis and Postgres both scale horizontally. Docker lets us add more workers behind a load balancer."

**Reliability:**
> "Every layer has graceful degradation: Redis fails → in-memory fallback. Twilio fails → retry with SMS. Calendar down → mock availability. The system never crashes."

---

## License

MIT License — Built for learning and portfolio demonstration.

**Lokesh Gaddam** | AI Automation Engineer Journey | Day 14-16
