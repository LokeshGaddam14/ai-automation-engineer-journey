# Day 12 — Twilio Phone Number + Bolna AI Integration

Connect Aria to a real Indian phone number so patients can call her directly — powered by **Bolna AI** instead of Vapi.

---

## Architecture

```
Patient calls +91 XXXXXXXXXX
        ↓
Twilio DID receives call
        ↓
Twilio webhook → Bolna AI inbound handler
        ↓
Bolna AI runs Aria agent (your Custom LLM via tools/webhook)
        ↓
FastAPI (ngrok) → LangGraph → answer
```

---

## Prerequisites

- [ ] Twilio account (sign up free at twilio.com — $15 trial credit)
- [ ] Bolna AI account at [platform.bolna.ai](https://platform.bolna.ai)
- [ ] FastAPI server running (`python -m uvicorn day10_fastapi.day10_api:app --reload --port 8000`)
- [ ] ngrok running (`ngrok http 8000`) with URL copied

---

## Step 1: Buy an Indian Phone Number in Twilio

1. Go to [Twilio Console → Buy a Number](https://console.twilio.com/us1/develop/phone-numbers/manage/search)
2. Set **Country: India** → Search
3. Pick any local number (~$1/month) → click **Buy**
4. Confirm purchase

> **Note:** Twilio trial accounts can buy numbers but can only call verified numbers.  
> To remove this restriction, upgrade to a paid account ($20 minimum).

---

## Step 2: Create an Agent in Bolna

1. Go to [platform.bolna.ai](https://platform.bolna.ai) → **Agents** → **Create Agent**
2. Name it **Aria**
3. Configure:
   - **Agent tab** → Welcome message:  
     `"Hi, this is Aria from Naveen Dental Clinic, how can I help you?"`
   - **LLM tab** → Select model (GPT-4o recommended) + connect your OpenAI key
   - **Audio tab** → Pick a voice (e.g., ElevenLabs — Rachel)
   - **Call tab** → Set Telephony Provider: **Twilio**
4. Click **Save**
5. Copy your **Agent ID** from the URL or the agent settings page

---

## Step 3: Add Credentials to `.env`

Add these to your `.env` file:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+91XXXXXXXXXX
NGROK_URL=https://your-ngrok-url.ngrok-free.app

# Bolna AI
BOLNA_API_KEY=your_bolna_api_key_here
BOLNA_AGENT_ID=your_bolna_agent_uuid_here
BOLNA_USER_ID=your_bolna_user_uuid_here   # optional — found in Bolna dashboard URL
```

- Twilio creds: https://console.twilio.com → Dashboard  
- Bolna API key: https://platform.bolna.ai → Settings → API Keys  
- Bolna Agent ID: Visible in the agent's URL (`/agent/<agent_id>`)

---

## Step 4: Install Dependencies

```powershell
pip install twilio requests
```

---

## Step 5: Run the Setup Script

```powershell
cd C:\Users\lokes\OneDrive\Desktop\ai-automation
python day12_phone/day12_phone_setup.py
```

This script will:
- ✅ Verify your Twilio credentials
- ✅ List your phone numbers
- ✅ Set Twilio voice webhook → Bolna AI inbound URL
- ✅ Check ngrok/FastAPI is reachable
- ✅ Verify your Bolna agent exists
- ✅ Print Bolna dashboard steps

---

## Step 6: Configure Inbound in Bolna Dashboard

### Option A — Using Bolna's Built-in Twilio Connection (Easiest)
1. Go to [platform.bolna.ai](https://platform.bolna.ai) → **Settings** → **Providers**
2. Click **Add Provider** → Choose **Twilio**
3. Enter Account SID + Auth Token
4. Bolna will automatically manage webhook routing

### Option B — Manual Twilio Webhook (What the script does)
The script auto-sets your Twilio number's webhook to:
```
https://api.bolna.ai/inbound_call?agent_id=<YOUR_AGENT_ID>
```

### Option C — Via Bolna Inbound Tab
1. Open your agent → **Inbound tab**
2. Toggle **Enable Inbound** → copy the displayed URL
3. Paste it into Twilio Console → your number → Voice webhook

---

## Step 7: Set Up Webhook Logging (Day 13)

In Bolna Dashboard → Agent → **Analytics tab**:
- **Push all execution data to webhook**: `https://your-ngrok-url.ngrok-free.app/bolna/webhook`

This triggers on every call end and logs to `call_logs.json`.

---

## Step 8: Test the Call

Call your Twilio number from your mobile.  
You should hear Aria's greeting:  
> *"Hi, this is Aria from Naveen Dental Clinic, how can I help you?"*

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Aria doesn't answer | Check Twilio webhook is set to the Bolna inbound URL |
| "Agent not found" | Verify BOLNA_AGENT_ID is correct (UUID format) |
| Twilio trial restriction | Verify your personal number in Twilio or upgrade account |
| Call connects but silent | Check Bolna agent has Voice and Welcome Message set |
| No slots / LLM error | Check FastAPI is running and ngrok URL is current |

---

## Bolna Inbound URL Format

```
https://api.bolna.ai/inbound_call?agent_id=<AGENT_ID>&user_id=<USER_ID>
```

This is Bolna's fixed endpoint. Twilio forwards the call here, Bolna handles it.

> **IP Whitelist (if needed):** Allow `13.203.39.153` for Bolna webhook calls.

---

## Next: Day 13 — Call Logging

Every call that ends fires a webhook to `/bolna/webhook` → logged to `call_logs.json`.  
See `day13_webhook/` for the full logger.
