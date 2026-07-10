# Day 11 — Bolna AI Voice Integration

Connect Aria's FastAPI + LangGraph backend to **Bolna AI** as a Custom LLM, enabling real voice conversations.

---

## What You're Building

```
You speak  →  Bolna AI  →  (ngrok tunnel)  →  FastAPI /v1/chat/completions
                                                       ↓
                                               LangGraph classifies
                                                       ↓
                                          RAG (pricing/hours) or Tool Agent (booking)
                                                       ↓
           Aria speaks  ←  Bolna TTS  ←  JSON response (OpenAI format)
```

Bolna handles the voice layer (microphone → speech-to-text → your LLM → text-to-speech → speaker).  
Your FastAPI server is the brain.

---

## Prerequisites

- [ ] FastAPI server working from Day 10
- [ ] Bolna AI account at [platform.bolna.ai](https://platform.bolna.ai) (free tier works)
- [ ] ngrok installed (`choco install ngrok` or download from ngrok.com)

---

## Step 1: Start FastAPI

```powershell
cd C:\Users\lokes\OneDrive\Desktop\ai-automation
python -m uvicorn day10_fastapi.day10_api:app --reload --port 8000
```

Verify it's running:
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing
```
Expected: `{"status":"healthy"}`

---

## Step 2: Start ngrok

```powershell
ngrok http 8000
```

Copy the `https://` URL shown (e.g. `https://sulfite-gecko-regular.ngrok-free.app`)  
Add it to your `.env`:
```
NGROK_URL=https://your-ngrok-url.ngrok-free.app
```

> **⚠️ Free tier:** ngrok URL changes every restart. Update `.env` + Bolna dashboard each time.

---

## Step 3: Add Bolna Credentials to `.env`

```
BOLNA_API_KEY=your_bolna_api_key_here
BOLNA_AGENT_ID=your_bolna_agent_uuid_here    # filled after Step 4
BOLNA_USER_ID=your_bolna_user_uuid_here      # optional
```

Get your API key: [platform.bolna.ai](https://platform.bolna.ai) → Settings → API Keys

---

## Step 4: Run the Setup Script

```powershell
cd C:\Users\lokes\OneDrive\Desktop\ai-automation
python day11_bolna/day11_bolna_setup.py
```

This script will:
- ✅ Verify FastAPI is running
- ✅ Verify ngrok is reachable
- ✅ Test the `/v1/chat/completions` endpoint
- ✅ Create the Aria agent in Bolna via API (if `BOLNA_API_KEY` is set)
- ✅ Print dashboard configuration steps
- ✅ Simulate a full 4-turn voice call

---

## Step 5: Configure Aria in Bolna Dashboard

Go to [platform.bolna.ai](https://platform.bolna.ai) → **Agents** → **Create Agent**

### Agent Tab
| Setting | Value |
|---------|-------|
| Agent name | Aria — Naveen Dental Clinic |
| Welcome message | `Hi, this is Aria from Naveen Dental Clinic, how can I help you?` |

### LLM Tab
| Setting | Value |
|---------|-------|
| LLM Provider | Custom (add your own) |
| LLM URL | `https://your-ngrok-url.ngrok-free.app/v1/chat/completions` |
| Model name | `aria` |
| Temperature | 0 |
| Max tokens | 200 |

**System Prompt:**
```
You are Aria, a friendly AI receptionist for Naveen Advanced Dental Clinic.
You help patients with appointment booking, pricing questions, clinic hours, and general inquiries.
Keep responses SHORT and NATURAL — this is a voice call, not a chat.
Never use bullet points or markdown. Speak like a real person on a phone call.
```

### Audio Tab
| Setting | Value |
|---------|-------|
| Language | English |
| Transcriber | Deepgram Nova 3 |
| Voice Provider | ElevenLabs or Azure |
| Voice | Rachel (ElevenLabs) or en-IN-NeerjaNeural (Azure) |

### Analytics Tab
| Setting | Value |
|---------|-------|
| Webhook URL | `https://your-ngrok-url.ngrok-free.app/bolna/webhook` |

---

## Step 6: Test with the Talk Button

1. Save the agent in Bolna dashboard
2. Click the **TALK** button (headphone icon)
3. Speak: *"How much does a root canal cost?"*
4. Aria should reply with the pricing from the FAQ
5. Speak: *"Can I book an appointment for tomorrow?"*
6. Aria should check availability and offer slots

---

## How the Custom LLM Endpoint Works

Bolna sends a standard OpenAI Chat Completions POST request to your server:

```json
POST /v1/chat/completions
{
  "model": "aria",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "How much does a root canal cost?"}
  ],
  "session_id": "bolna-call-abc123"
}
```

Your FastAPI extracts the user message → runs it through LangGraph → responds in OpenAI format:

```json
{
  "id": "chatcmpl-xyz",
  "object": "chat.completion",
  "model": "aria",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Root canal treatment costs between ₹4,000 and ₹8,000..."},
    "finish_reason": "stop"
  }]
}
```

Bolna converts this text to speech and plays it back to the caller.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Bolna says "I couldn't understand" | Check ngrok URL in Bolna dashboard LLM tab |
| FastAPI not reachable | Run `ngrok http 8000` and update `NGROK_URL` in `.env` |
| 502 Bad Gateway from ngrok | FastAPI server not running — start it first |
| Aria responds but takes too long | Normal — LangGraph + Groq adds ~2-3s latency |
| ngrok URL changed | Restart ngrok, copy new URL, update Bolna LLM URL, update `.env` |

---

## Endpoints Added (Day 11)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | Bolna Custom LLM endpoint (OpenAI format) |
| `/bolna/webhook` | POST | Receives Bolna call execution events |
| `/chat` | POST | Standard JSON chat (unchanged from Day 10) |
| `/health` | GET | Health check |

---

## Next: Day 12 — Real Phone Number

Give Aria a real Indian phone number (+91) so patients can call her directly.  
See `day12_phone/README_phone_setup.md`
