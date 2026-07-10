# -*- coding: utf-8 -*-
"""
Day 11 - Aria: Chat + Call Test Script
=======================================
Two modes:
  1. CHAT  - Send text messages to Aria via FastAPI /chat endpoint
  2. CALL  - Trigger an outbound voice call via Bolna AI API

Usage:
    python day11_bolna/day11_test_chat_and_call.py            # runs both tests
    python day11_bolna/day11_test_chat_and_call.py --chat     # chat only
    python day11_bolna/day11_test_chat_and_call.py --call     # call only

Requirements:
    pip install requests python-dotenv
"""

import os
import sys
import json
import uuid
import time
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Config (from .env)
# ─────────────────────────────────────────────
FASTAPI_URL    = "http://127.0.0.1:8000"
BOLNA_API_KEY  = os.getenv("BOLNA_API_KEY", "")
BOLNA_AGENT_ID = os.getenv("BOLNA_AGENT_ID", "")
BOLNA_BASE_URL = "https://api.bolna.ai"

# Phone number to call (set in .env or override below)
# Must be verified in Bolna/Twilio for trial accounts
PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "") or os.getenv("TEST_PHONE_NUMBER", "")


# ═══════════════════════════════════════════════
#  PART 1 — CHAT TEST (FastAPI /chat endpoint)
# ═══════════════════════════════════════════════

def run_chat_test():
    """
    Simulate a multi-turn text conversation with Aria via FastAPI.
    Uses the /chat endpoint — no voice, no Bolna required.
    Great for testing LangGraph logic quickly.
    """
    print("\n" + "="*60)
    print("CHAT TEST — Aria via FastAPI /chat")
    print("="*60)

    # Check FastAPI is up
    try:
        r = requests.get(f"{FASTAPI_URL}/health", timeout=5)
        if r.status_code != 200:
            print(f"[ERROR] FastAPI not healthy: {r.status_code}")
            return
        print(f"[OK] FastAPI is running at {FASTAPI_URL}")
    except Exception as e:
        print(f"[ERROR] FastAPI not reachable: {e}")
        print(f"   Start it: python -m uvicorn day10_fastapi.day10_api:app --reload --port 8000")
        return

    session_id = f"chat-test-{uuid.uuid4().hex[:8]}"
    print(f"[INFO] Session ID: {session_id}\n")

    # Test conversation
    test_messages = [
        ("PRICING",       "How much does a root canal cost?"),
        ("HOURS",         "What are your clinic hours?"),
        ("BOOKING",       "Can I book an appointment for tomorrow at 10 AM?"),
        ("BOOKING CONT.", "My name is Lokesh"),
        ("EMERGENCY",     "I have severe tooth pain right now, what should I do?"),
        ("GENERAL",       "Do you accept UPI payments?"),
    ]

    results = []
    for intent_label, message in test_messages:
        print(f"  Patient [{intent_label}]: {message}")
        try:
            resp = requests.post(
                f"{FASTAPI_URL}/chat",
                json={"message": message, "session_id": session_id},
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                reply   = data.get("response", "")
                intent  = data.get("intent", "unknown")
                # Truncate long responses for display
                display = reply[:120] + "..." if len(reply) > 120 else reply
                print(f"  Aria   [{intent}]: {display}")
                results.append({"status": "ok", "intent": intent})
            else:
                print(f"  [ERROR] {resp.status_code}: {resp.text[:100]}")
                results.append({"status": "error"})
        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({"status": "error"})
        print()
        time.sleep(0.5)  # small delay between turns

    passed = sum(1 for r in results if r["status"] == "ok")
    print(f"[RESULT] {passed}/{len(test_messages)} messages handled successfully")
    return passed == len(test_messages)


# ═══════════════════════════════════════════════
#  PART 2 — OUTBOUND CALL (Bolna API)
# ═══════════════════════════════════════════════

def run_call_test(phone_number: str = None):
    """
    Trigger an outbound voice call using Bolna AI API.
    Bolna will call the specified phone number and connect to Aria.

    Requires:
        - BOLNA_API_KEY set in .env
        - BOLNA_AGENT_ID set in .env
        - A phone number to call
    """
    print("\n" + "="*60)
    print("CALL TEST — Outbound call via Bolna AI")
    print("="*60)

    # Validate prerequisites
    if not BOLNA_API_KEY or BOLNA_API_KEY == "your_bolna_api_key_here":
        print("[ERROR] BOLNA_API_KEY not set in .env")
        print("   Get it from: platform.bolna.ai -> Settings -> API Keys")
        return False

    if not BOLNA_AGENT_ID or BOLNA_AGENT_ID == "your_bolna_agent_uuid_here":
        print("[ERROR] BOLNA_AGENT_ID not set in .env")
        print("   Get it from: platform.bolna.ai -> Studio -> your agent -> URL")
        return False

    to_number = phone_number or PHONE_NUMBER
    if not to_number or "XXXXXXXXXX" in to_number:
        print("[ERROR] No phone number to call!")
        print("   Set TEST_PHONE_NUMBER=+91XXXXXXXXXX in your .env")
        print("   Or pass --number +91XXXXXXXXXX as argument")
        print()
        print("   Example: python day11_bolna/day11_test_chat_and_call.py --call --number +919876543210")
        return False

    print(f"[INFO] Agent ID  : {BOLNA_AGENT_ID}")
    print(f"[INFO] Calling   : {to_number}")
    print(f"[INFO] Bolna API : {BOLNA_BASE_URL}")
    print()

    headers = {
        "Authorization": f"Bearer {BOLNA_API_KEY}",
        "Content-Type": "application/json"
    }

    # Bolna outbound call payload
    call_payload = {
        "agent_id": BOLNA_AGENT_ID,
        "recipient_phone_number": to_number,
        "user_data": {
            "call_purpose": "appointment_inquiry",
            "initiated_by": "day11_test_script",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

    print(f"[SENDING] POST {BOLNA_BASE_URL}/call")
    print(f"  Payload: {json.dumps(call_payload, indent=2)}\n")

    try:
        resp = requests.post(
            f"{BOLNA_BASE_URL}/call",
            headers=headers,
            json=call_payload,
            timeout=30
        )

        print(f"[RESPONSE] Status: {resp.status_code}")

        if resp.status_code in (200, 201, 202):
            data = resp.json()
            call_id     = data.get("call_id") or data.get("execution_id") or data.get("id", "unknown")
            call_status = data.get("status") or data.get("call_status", "initiated")

            print(f"[OK] Call initiated successfully!")
            print(f"   Call ID     : {call_id}")
            print(f"   Status      : {call_status}")
            print(f"   Calling     : {to_number}")
            print()
            print("[INFO] Your phone should ring in a few seconds...")
            print("[INFO] Aria will greet you: 'Hi, this is Aria from Naveen Dental Clinic!'")
            print()
            print("Test questions to ask Aria on the call:")
            print("  - 'How much does a root canal cost?'")
            print("  - 'What are your clinic hours?'")
            print("  - 'Can I book an appointment for tomorrow?'")

            # Poll call status (optional — up to 30s)
            if call_id and call_id != "unknown":
                print()
                print("[INFO] Monitoring call status for 30 seconds...")
                _poll_call_status(call_id, headers, duration=30)

            return True

        else:
            print(f"[ERROR] Bolna returned {resp.status_code}")
            print(f"   Response: {resp.text[:500]}")
            _print_call_troubleshoot(resp.status_code)
            return False

    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot reach Bolna API ({BOLNA_BASE_URL})")
        print("   Check your internet connection")
        return False
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return False


def _poll_call_status(call_id: str, headers: dict, duration: int = 30):
    """Poll Bolna call execution status until completed or timeout."""
    start = time.time()
    last_status = ""

    while time.time() - start < duration:
        try:
            resp = requests.get(
                f"{BOLNA_BASE_URL}/v2/execution/{call_id}",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                data   = resp.json()
                status = data.get("call_status") or data.get("status", "unknown")

                if status != last_status:
                    elapsed = round(time.time() - start, 1)
                    print(f"   [{elapsed}s] Status: {status}")
                    last_status = status

                if status in ("completed", "failed", "no-answer", "busy", "canceled"):
                    if status == "completed":
                        duration_s = data.get("conversation_time", "N/A")
                        print(f"\n[OK] Call completed! Duration: {duration_s}s")
                        transcript = data.get("transcript", "")
                        if transcript:
                            print(f"\n--- Transcript (last 500 chars) ---")
                            print(transcript[-500:])
                            print("-----------------------------------")
                    else:
                        print(f"\n[INFO] Call ended with status: {status}")
                    return
        except Exception:
            pass
        time.sleep(5)

    print(f"\n[INFO] Polling stopped after {duration}s (call may still be in progress)")
    print(f"   View full details at: platform.bolna.ai -> Call History")


def _print_call_troubleshoot(status_code: int):
    tips = {
        400: "Bad request — check BOLNA_AGENT_ID format (must be UUID)",
        401: "Unauthorized — check BOLNA_API_KEY in .env",
        403: "Forbidden — your plan may not support outbound calls",
        404: "Agent not found — check BOLNA_AGENT_ID",
        422: "Validation error — check phone number format (e.g. +919876543210)",
        429: "Rate limit exceeded — wait a minute and retry",
        500: "Bolna server error — try again in a minute",
    }
    tip = tips.get(status_code, "Check Bolna dashboard for details")
    print(f"   Tip: {tip}")


# ═══════════════════════════════════════════════
#  INTERACTIVE CHAT (manual mode)
# ═══════════════════════════════════════════════

def run_interactive_chat():
    """
    Interactive terminal chat with Aria (no voice).
    Type your message, Aria responds. Type 'quit' to exit.
    """
    print("\n" + "="*60)
    print("INTERACTIVE CHAT — Type messages to Aria")
    print("Type 'quit' or 'exit' to stop")
    print("="*60)

    try:
        r = requests.get(f"{FASTAPI_URL}/health", timeout=5)
        if r.status_code != 200:
            print(f"[ERROR] FastAPI not running")
            return
    except Exception as e:
        print(f"[ERROR] FastAPI not reachable: {e}")
        return

    session_id = f"interactive-{uuid.uuid4().hex[:8]}"
    print(f"[Session: {session_id}]\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[Goodbye!]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print("Aria: Goodbye! Have a great day!")
            break

        try:
            resp = requests.post(
                f"{FASTAPI_URL}/chat",
                json={"message": user_input, "session_id": session_id},
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                print(f"Aria [{data.get('intent','?')}]: {data.get('response', '')}\n")
            else:
                print(f"[ERROR] {resp.status_code}: {resp.text[:100]}\n")
        except Exception as e:
            print(f"[ERROR] {e}\n")


# ═══════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Aria Day 11 — Chat & Call Test Script"
    )
    parser.add_argument("--chat",   action="store_true", help="Run automated chat test only")
    parser.add_argument("--call",   action="store_true", help="Run outbound call test only")
    parser.add_argument("--live",   action="store_true", help="Run interactive chat in terminal")
    parser.add_argument("--number", type=str, default="",
                        help="Phone number to call (e.g. +919876543210)")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  Aria - Day 11: Chat + Call Test")
    print(f"  FastAPI : {FASTAPI_URL}")
    print(f"  Bolna   : {BOLNA_BASE_URL}")
    print(f"  Agent ID: {BOLNA_AGENT_ID or 'NOT SET'}")
    print("="*60)

    if args.live:
        run_interactive_chat()

    elif args.chat:
        run_chat_test()

    elif args.call:
        number = args.number or PHONE_NUMBER
        if not number:
            print("\n[ERROR] Provide a phone number with --number +91XXXXXXXXXX")
            sys.exit(1)
        run_call_test(phone_number=number)

    else:
        # Default: run both tests
        chat_ok = run_chat_test()
        print()
        call_ok = run_call_test(phone_number=args.number)

        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"  Chat test : {'PASSED' if chat_ok else 'FAILED / SKIPPED'}")
        print(f"  Call test : {'PASSED' if call_ok else 'FAILED / SKIPPED (no phone number?)'}")
        print()
        print("Next steps:")
        print("  1. Open platform.bolna.ai -> Studio -> Aria -> Click 'Chat with agent'")
        print("  2. Or click 'Get call from agent' to hear Aria's voice")
        print("  3. Day 12: Set up a real Indian phone number with Twilio")
        print("="*60)
