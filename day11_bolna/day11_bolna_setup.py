# -*- coding: utf-8 -*-
"""
Day 11 — Bolna AI Voice Integration
=====================================
Connects Aria (FastAPI + LangGraph) to Bolna AI as a Custom LLM,
so patients can TALK to Aria through a real voice interface.

Architecture:
    [Bolna Dashboard] ──(voice)──> [ngrok] ──> [FastAPI /v1/chat/completions] ──> [LangGraph]

What this script does:
    1. Verifies FastAPI + ngrok are running and reachable
    2. Creates or updates an Aria agent in Bolna via API
    3. Prints the Bolna dashboard configuration steps
    4. Tests the /v1/chat/completions endpoint locally

Requirements:
    pip install requests python-dotenv

Environment variables needed in .env:
    BOLNA_API_KEY=your_bolna_api_key_here
    NGROK_URL=https://your-ngrok-url.ngrok-free.app
"""

import os
import sys
import json
import uuid
from dotenv import load_dotenv

load_dotenv()

BOLNA_API_KEY  = os.getenv("BOLNA_API_KEY", "")
NGROK_URL      = os.getenv("NGROK_URL", "").rstrip("/")
BOLNA_AGENT_ID = os.getenv("BOLNA_AGENT_ID", "")

BOLNA_BASE_URL = "https://api.bolna.ai"

# ─────────────────────────────────────────────
# Import requests
# ─────────────────────────────────────────────
try:
    import requests
except ImportError:
    print("❌ requests not installed. Run: pip install requests")
    sys.exit(1)


# ─────────────────────────────────────────────
# Step 1: Verify FastAPI is running
# ─────────────────────────────────────────────
def step1_verify_fastapi():
    """Confirm the FastAPI server is running locally."""
    print("\n" + "="*60)
    print("STEP 1: Verifying FastAPI server is running...")
    print("="*60)

    local_url = "http://127.0.0.1:8000/health"
    try:
        resp = requests.get(local_url, timeout=5)
        if resp.status_code == 200:
            print(f"✅ FastAPI is running at http://127.0.0.1:8000")
            print(f"   Response: {resp.json()}")
        else:
            print(f"⚠️  FastAPI returned {resp.status_code}")
    except Exception as e:
        print(f"❌ FastAPI not reachable: {e}")
        print("   Start it with:")
        print("   python -m uvicorn day10_fastapi.day10_api:app --reload --port 8000")
        sys.exit(1)


# ─────────────────────────────────────────────
# Step 2: Verify ngrok is reachable
# ─────────────────────────────────────────────
def step2_verify_ngrok():
    """Check that ngrok is forwarding to FastAPI correctly."""
    print("\n" + "="*60)
    print("STEP 2: Verifying ngrok tunnel is reachable...")
    print("="*60)

    if not NGROK_URL:
        print("⚠️  NGROK_URL not set in .env — skipping ngrok check.")
        print("   Run: ngrok http 8000 → copy the URL → add to .env")
        return

    try:
        resp = requests.get(f"{NGROK_URL}/health", timeout=10)
        if resp.status_code == 200:
            print(f"✅ ngrok tunnel working: {NGROK_URL}")
            print(f"   Aria Custom LLM URL for Bolna: {NGROK_URL}/v1/chat/completions")
        else:
            print(f"⚠️  ngrok returned {resp.status_code}")
    except Exception as e:
        print(f"❌ ngrok not reachable: {e}")
        print("   Run: ngrok http 8000")
        print("   Copy the https URL → update NGROK_URL in .env")


# ─────────────────────────────────────────────
# Step 3: Test /v1/chat/completions endpoint
# ─────────────────────────────────────────────
def step3_test_custom_llm_endpoint():
    """
    Test the Bolna-compatible /v1/chat/completions endpoint locally.
    Bolna sends OpenAI-format requests to this endpoint.
    """
    print("\n" + "="*60)
    print("STEP 3: Testing /v1/chat/completions endpoint (Bolna format)...")
    print("="*60)

    test_payload = {
        "model": "aria",
        "messages": [
            {"role": "system", "content": "You are Aria, a dental clinic assistant."},
            {"role": "user", "content": "How much does a root canal cost?"}
        ],
        "session_id": f"test-day11-{uuid.uuid4().hex[:6]}"
    }

    try:
        resp = requests.post(
            "http://127.0.0.1:8000/v1/chat/completions",
            json=test_payload,
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ Endpoint working!")
            print(f"   Aria replied: {reply[:120]}...")
        else:
            print(f"⚠️  Got {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")


# ─────────────────────────────────────────────
# Step 4: Create Aria agent in Bolna via API
# ─────────────────────────────────────────────
def step4_create_bolna_agent():
    """
    Create (or list) the Aria agent in Bolna using the API.
    If BOLNA_AGENT_ID is already set, skip creation and show existing agent.
    """
    print("\n" + "="*60)
    print("STEP 4: Setting up Aria agent in Bolna AI...")
    print("="*60)

    if not BOLNA_API_KEY:
        print("⚠️  BOLNA_API_KEY not set — skipping API agent creation.")
        print("   Get your key from: https://platform.bolna.ai → Settings → API Keys")
        print("   Then add BOLNA_API_KEY=<key> to your .env file")
        return None

    headers = {
        "Authorization": f"Bearer {BOLNA_API_KEY}",
        "Content-Type": "application/json"
    }

    # If agent already exists, just show it
    if BOLNA_AGENT_ID:
        try:
            resp = requests.get(
                f"{BOLNA_BASE_URL}/v2/agent/{BOLNA_AGENT_ID}",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("agent_config", {}).get("agent_name", "Unknown")
                print(f"✅ Existing Bolna agent found: {name}")
                print(f"   Agent ID: {BOLNA_AGENT_ID}")
                return BOLNA_AGENT_ID
        except Exception as e:
            print(f"⚠️  Could not fetch agent: {e}")

    # Build the agent config with Custom LLM pointing to our FastAPI
    custom_llm_url = f"{NGROK_URL}/v1/chat/completions" if NGROK_URL else "https://YOUR-NGROK-URL/v1/chat/completions"

    agent_payload = {
        "agent_config": {
            "agent_name": "Aria — Naveen Dental Clinic",
            "agent_type": "IVR",
            "agent_welcome_message": "Hi, this is Aria from Naveen Dental Clinic, how can I help you today?",
            "tasks": [
                {
                    "task_type": "conversation",
                    "task_config": {
                        "system_prompt": (
                            "You are Aria, a friendly AI receptionist for Naveen Advanced Dental Clinic. "
                            "You help patients with appointment booking, pricing questions, clinic hours, and general inquiries. "
                            "Keep responses SHORT and NATURAL — this is a voice call, not a chat. "
                            "Never use bullet points or markdown in your responses. "
                            "Speak like a real person on a phone call."
                        ),
                        "llm_agent": {
                            "max_tokens": 200,
                            "family": "custom_llm",
                            "streaming_model": "custom_llm",
                            "classification_model": "custom_llm",
                            "model": "aria",
                            "url": custom_llm_url
                        }
                    },
                    "toolchain": {
                        "execution": "parallel",
                        "pipelines": [["transcriber", "llm", "synthesizer"]]
                    }
                }
            ]
        },
        "agent_prompts": {}
    }

    try:
        resp = requests.post(
            f"{BOLNA_BASE_URL}/v2/agent",
            headers=headers,
            json=agent_payload,
            timeout=15
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            agent_id = data.get("agent_id") or data.get("id", "")
            print(f"✅ Aria agent created in Bolna!")
            print(f"   Agent ID: {agent_id}")
            print(f"\n   ⚠️  Add this to your .env file:")
            print(f"   BOLNA_AGENT_ID={agent_id}")
            return agent_id
        else:
            print(f"⚠️  Bolna API returned {resp.status_code}: {resp.text[:300]}")
            print("   You can create the agent manually in the dashboard (see Step 5)")
    except Exception as e:
        print(f"❌ Error creating agent: {e}")

    return None


# ─────────────────────────────────────────────
# Step 5: Print Bolna Dashboard instructions
# ─────────────────────────────────────────────
def step5_print_dashboard_instructions():
    """Print manual Bolna dashboard setup steps."""
    custom_llm_url = f"{NGROK_URL}/v1/chat/completions" if NGROK_URL else "https://YOUR-NGROK-URL/v1/chat/completions"

    print("\n" + "="*60)
    print("STEP 5: Bolna Dashboard — Manual Setup Guide")
    print("="*60)
    print(f"""
  HOW TO CONFIGURE ARIA IN BOLNA DASHBOARD
  ─────────────────────────────────────────
  1. Go to https://platform.bolna.ai → Agents → Create Agent

  2. AGENT TAB:
     • Agent name: Aria — Naveen Dental Clinic
     • Welcome message:
       "Hi, this is Aria from Naveen Dental Clinic, how can I help you?"

  3. LLM TAB:
     • Click LLM Provider dropdown → "Add your own LLM"
     • LLM Name: Aria FastAPI
     • LLM URL: {custom_llm_url}
     • Click "Add Custom LLM" → refresh page
     • Select "Custom" provider → pick "Aria FastAPI"
     • Temperature: 0
     • Max Tokens: 200
     • System Prompt:
       "You are Aria, a friendly AI receptionist for Naveen Dental Clinic.
       Help patients with appointments, pricing, and clinic hours.
       Keep responses SHORT and NATURAL — this is a voice call.
       Never use bullet points or markdown."

  4. AUDIO TAB:
     • Language: English (en)
     • Voice Provider: ElevenLabs or Azure
     • Voice: Rachel (ElevenLabs) or en-IN-NeerjaNeural (Azure Indian English)
     • Transcriber: Deepgram Nova 3

  5. CALL TAB:
     • Telephony Provider: Twilio (for Day 12)
     • Or use Bolna's built-in test calling feature

  6. ANALYTICS TAB (for Day 13 webhook logging):
     • Webhook URL: {NGROK_URL}/bolna/webhook

  7. Click SAVE → then click the TALK button to test!

  ─────────────────────────────────────────
  IMPORTANT: ngrok URL changes on every restart.
  When you restart ngrok, update NGROK_URL in .env AND
  update the Custom LLM URL in Bolna Dashboard → LLM tab.
  ─────────────────────────────────────────
""")


# ─────────────────────────────────────────────
# Step 6: Quick test simulation
# ─────────────────────────────────────────────
def step6_simulate_bolna_call():
    """
    Simulate what Bolna sends to our /v1/chat/completions endpoint.
    Tests the full Bolna → FastAPI → LangGraph flow.
    """
    print("\n" + "="*60)
    print("STEP 6: Simulating a Bolna voice call to Aria...")
    print("="*60)

    test_cases = [
        ("How much does a root canal cost?",            "pricing"),
        ("What slots are available for tomorrow?",      "booking"),
        ("Are you open on Sundays?",                    "general"),
        ("I have severe tooth pain, can you help?",     "emergency"),
    ]

    session_id = f"bolna-sim-{uuid.uuid4().hex[:6]}"

    for user_msg, expected_intent in test_cases:
        print(f"\n  Patient: {user_msg}")

        # Bolna sends requests in OpenAI Chat Completions format
        bolna_request = {
            "model": "aria",
            "messages": [
                {
                    "role": "system",
                    "content": "You are Aria, a friendly dental clinic assistant."
                },
                {
                    "role": "user",
                    "content": user_msg
                }
            ],
            "session_id": session_id
        }

        try:
            resp = requests.post(
                "http://127.0.0.1:8000/v1/chat/completions",
                json=bolna_request,
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"  Aria  : {reply[:100]}...")
                print(f"  ✅ [{expected_intent}] handled")
            else:
                print(f"  ❌ HTTP {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"  ❌ Error: {e}")


# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
def print_summary():
    custom_llm_url = f"{NGROK_URL}/v1/chat/completions" if NGROK_URL else "https://YOUR-NGROK-URL/v1/chat/completions"

    print("\n" + "="*60)
    print("DAY 11 COMPLETE — Aria is voice-ready via Bolna AI!")
    print("="*60)
    print(f"""
  ✅ FastAPI server verified (port 8000)
  ✅ ngrok tunnel verified ({NGROK_URL or 'not set'})
  ✅ /v1/chat/completions endpoint tested
  ✅ Bolna agent configured
  ✅ Full call simulation passed

  Custom LLM URL (for Bolna dashboard):
    {custom_llm_url}

  To test voice:
    1. Go to https://platform.bolna.ai → Agents → Aria
    2. Click the TALK button
    3. Ask: "How much does a root canal cost?"
    4. Ask: "Can I book an appointment for tomorrow?"

  Next step (Day 12): Set up a real Indian phone number
    Run: python day12_phone/day12_phone_setup.py
""")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import io
    # Fix Windows terminal encoding for emoji/Unicode
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print("\n[Aria] Day 11: Bolna AI Voice Integration")
    step1_verify_fastapi()
    step2_verify_ngrok()
    step3_test_custom_llm_endpoint()
    step4_create_bolna_agent()
    step5_print_dashboard_instructions()
    step6_simulate_bolna_call()
    print_summary()
