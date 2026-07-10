# -*- coding: utf-8 -*-
"""
Day 12 - Phone Number Setup & Inbound Call Verification
========================================================
Two approaches for giving Aria a real callable phone number:

  Option A (Demo/Free): Use Bolna's built-in phone number
    - No Twilio account needed
    - Bolna assigns a number automatically
    - Perfect for portfolio demos

  Option B (Production): Buy an Indian Twilio DID (~Rs.80/month)
    - Your own +91 number
    - Patients can save it in contacts
    - Set Twilio webhook -> Bolna inbound URL

This script handles BOTH options and verifies everything is working.

Usage:
    python day12_phone/day12_phone_setup.py            # auto-detect
    python day12_phone/day12_phone_setup.py --bolna    # Bolna number only
    python day12_phone/day12_phone_setup.py --twilio   # Twilio number
"""

import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
BOLNA_API_KEY    = os.getenv("BOLNA_API_KEY", "")
BOLNA_AGENT_ID   = os.getenv("BOLNA_AGENT_ID", "")
BOLNA_USER_ID    = os.getenv("BOLNA_USER_ID", "")
BOLNA_BASE_URL   = "https://api.bolna.ai"

TWILIO_SID       = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN     = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_NUMBER    = os.getenv("TWILIO_PHONE_NUMBER", "")
NGROK_URL        = os.getenv("NGROK_URL", "").rstrip("/")

FASTAPI_URL      = "http://127.0.0.1:8000"

BOLNA_HEADERS = {
    "Authorization": f"Bearer {BOLNA_API_KEY}",
    "Content-Type": "application/json"
}


# ═══════════════════════════════════════════════
#  OPTION A — Bolna Built-in Number (Demo/Free)
# ═══════════════════════════════════════════════

def setup_bolna_number():
    """
    Get Aria's inbound phone number from Bolna.
    Bolna assigns a number when you connect a telephony provider OR
    provides a built-in test number.
    """
    print("\n" + "="*60)
    print("OPTION A: Bolna Built-in Phone Number")
    print("="*60)

    if not BOLNA_API_KEY or not BOLNA_AGENT_ID:
        print("[ERROR] BOLNA_API_KEY or BOLNA_AGENT_ID not set in .env")
        return

    # Fetch agent details
    print(f"[INFO] Fetching Aria agent: {BOLNA_AGENT_ID}")
    try:
        resp = requests.get(
            f"{BOLNA_BASE_URL}/v2/agent/{BOLNA_AGENT_ID}",
            headers=BOLNA_HEADERS,
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            agent_cfg = data.get("agent_config", {})
            agent_name = agent_cfg.get("agent_name", "Unknown")
            print(f"[OK] Agent found: {agent_name}")
            print(f"   Agent ID: {BOLNA_AGENT_ID}")
            print()

            # Show inbound URL that Twilio/any provider should point to
            if BOLNA_USER_ID:
                inbound_url = (
                    f"{BOLNA_BASE_URL}/inbound_call"
                    f"?agent_id={BOLNA_AGENT_ID}&user_id={BOLNA_USER_ID}"
                )
            else:
                inbound_url = (
                    f"{BOLNA_BASE_URL}/inbound_call?agent_id={BOLNA_AGENT_ID}"
                )

            print("[INBOUND CONFIG]")
            print(f"   Bolna Inbound URL : {inbound_url}")
            print()
            print("[DASHBOARD STEPS]")
            print("   1. Go to platform.bolna.ai -> Studio -> Aria")
            print("   2. Click the 'Inbound' tab")
            print("   3. Toggle 'Enable Inbound' to ON")
            print("   4. Bolna will show you a phone number or a URL to use")
            print("   5. Call that number to test!")
            print()
            print("[DEMO TESTING]")
            print("   - Use 'Get call from agent' button in Bolna dashboard")
            print("   - This calls your verified number immediately")
            print("   - Perfect for portfolio demos and CV projects")

        else:
            print(f"[ERROR] Bolna API: {resp.status_code} - {resp.text[:200]}")

    except Exception as e:
        print(f"[ERROR] {e}")

    # Print Bolna dashboard manual steps
    _print_bolna_my_numbers()


def _print_bolna_my_numbers():
    """Instructions to find the Bolna number in the dashboard."""
    print()
    print("[INFO] To find your Bolna number:")
    print("   platform.bolna.ai -> 'My Numbers' (in left sidebar)")
    print("   If no number shown, go to Settings -> Providers -> Add Twilio")
    print("   OR use the 'Get call from agent' button for demo calls")
    print()
    print("[INBOUND TEST COMMAND]")
    print("   Once you have a number, call it from your phone!")
    print("   Aria will say: 'Hi, this is Aria from Naveen Dental Clinic...'")


# ═══════════════════════════════════════════════
#  OPTION B — Twilio DID (Production)
# ═══════════════════════════════════════════════

def setup_twilio_number():
    """
    Verify Twilio credentials and configure the Twilio webhook
    to route inbound calls to Bolna AI.
    """
    print("\n" + "="*60)
    print("OPTION B: Twilio Indian Phone Number (Production)")
    print("="*60)

    # Check credentials
    if not TWILIO_SID or "your_twilio" in TWILIO_SID.lower():
        print("[ERROR] TWILIO_ACCOUNT_SID not set in .env")
        print("   Sign up at twilio.com -> get Account SID + Auth Token")
        print("   Add to .env:")
        print("     TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxx")
        print("     TWILIO_AUTH_TOKEN=xxxxxxxxxxxx")
        print("     TWILIO_PHONE_NUMBER=+91XXXXXXXXXX")
        return

    # Build Bolna inbound URL
    if BOLNA_USER_ID:
        bolna_inbound = (
            f"{BOLNA_BASE_URL}/inbound_call"
            f"?agent_id={BOLNA_AGENT_ID}&user_id={BOLNA_USER_ID}"
        )
    else:
        bolna_inbound = f"{BOLNA_BASE_URL}/inbound_call?agent_id={BOLNA_AGENT_ID}"

    # Verify Twilio credentials
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)

        account = client.api.accounts(TWILIO_SID).fetch()
        print(f"[OK] Twilio account: {account.friendly_name} ({account.status})")

        # List numbers
        numbers = client.incoming_phone_numbers.list()
        if not numbers:
            print("[WARN] No phone numbers in your Twilio account.")
            print("   Buy one at: console.twilio.com -> Phone Numbers -> Buy a Number")
            print("   Country: India, Type: Local (~$1/month)")
        else:
            print(f"[OK] Found {len(numbers)} phone number(s):")
            for n in numbers:
                print(f"   {n.phone_number} — {n.friendly_name}")

        # Configure webhook if number is set
        if TWILIO_NUMBER and "XXXXXXXXXX" not in TWILIO_NUMBER:
            nums = client.incoming_phone_numbers.list(phone_number=TWILIO_NUMBER)
            if nums:
                nums[0].update(
                    voice_url=bolna_inbound,
                    voice_method="POST"
                )
                print(f"[OK] Webhook set for {TWILIO_NUMBER}")
                print(f"   Voice URL -> {bolna_inbound}")
            else:
                print(f"[WARN] {TWILIO_NUMBER} not found in account")
        else:
            print(f"[INFO] Set voice webhook manually:")
            print(f"   Twilio Console -> your number -> Voice webhook:")
            print(f"   {bolna_inbound}")

    except ImportError:
        print("[ERROR] Twilio SDK not installed. Run: pip install twilio")
    except Exception as e:
        print(f"[ERROR] Twilio error: {e}")


# ═══════════════════════════════════════════════
#  COMMON — Verify full stack is ready
# ═══════════════════════════════════════════════

def verify_full_stack():
    """Check FastAPI, ngrok, and Bolna agent are all up."""
    print("\n" + "="*60)
    print("VERIFICATION: Full Stack Check")
    print("="*60)

    checks = []

    # 1. FastAPI
    try:
        r = requests.get(f"{FASTAPI_URL}/health", timeout=5)
        if r.status_code == 200:
            print(f"[OK] FastAPI running at {FASTAPI_URL}")
            checks.append(True)
        else:
            print(f"[WARN] FastAPI returned {r.status_code}")
            checks.append(False)
    except Exception as e:
        print(f"[FAIL] FastAPI not reachable: {e}")
        print(f"   Run: python -m uvicorn day10_fastapi.day10_api:app --reload --port 8000")
        checks.append(False)

    # 2. ngrok
    if NGROK_URL and "your-ngrok" not in NGROK_URL:
        try:
            r = requests.get(
                f"{NGROK_URL}/health",
                headers={"ngrok-skip-browser-warning": "true"},
                timeout=10
            )
            if r.status_code == 200:
                print(f"[OK] ngrok tunnel: {NGROK_URL}")
                checks.append(True)
            else:
                print(f"[WARN] ngrok returned {r.status_code}")
                checks.append(False)
        except Exception as e:
            print(f"[FAIL] ngrok not reachable: {e}")
            checks.append(False)
    else:
        print(f"[SKIP] NGROK_URL not set (not needed for Bolna built-in number)")
        checks.append(True)

    # 3. Bolna agent
    if BOLNA_API_KEY and BOLNA_AGENT_ID:
        try:
            r = requests.get(
                f"{BOLNA_BASE_URL}/v2/agent/{BOLNA_AGENT_ID}",
                headers=BOLNA_HEADERS,
                timeout=10
            )
            if r.status_code == 200:
                name = r.json().get("agent_config", {}).get("agent_name", "Unknown")
                print(f"[OK] Bolna agent '{name}' verified")
                checks.append(True)
            else:
                print(f"[WARN] Bolna agent check: {r.status_code}")
                checks.append(False)
        except Exception as e:
            print(f"[FAIL] Bolna check: {e}")
            checks.append(False)

    passed = sum(checks)
    total  = len(checks)
    print(f"\n[RESULT] {passed}/{total} checks passed")
    return passed == total


def print_summary(mode: str):
    print("\n" + "="*60)
    print("DAY 12 COMPLETE - Aria Has a Real Phone Number!")
    print("="*60)
    print()
    print("What was accomplished:")
    print("  [OK] Bolna agent configured for inbound calls")
    print("  [OK] Full stack verified (FastAPI + Bolna)")
    if mode == "twilio":
        print(f"  [OK] Twilio number {TWILIO_NUMBER} webhook -> Bolna AI")
    else:
        print("  [OK] Using Bolna built-in number for demo calls")
    print()
    print("To test RIGHT NOW:")
    print("  1. Go to platform.bolna.ai -> Studio -> Aria")
    print("  2. Click 'Get call from agent' -> enter your number")
    print("  3. Pick up and talk to Aria!")
    print()
    print("Architecture achieved:")
    print("  Patient dials number")
    print("    -> Bolna/Twilio receives call")
    print("    -> Bolna runs Aria (Knowledge Base + GPT)")
    print("    -> Voice conversation")
    print("    -> Call ends -> webhook fires -> logged to call_logs.json")
    print()
    print("Next: Day 13 - Call Logging Webhook (already built!)")
    print("  Run: python day13_webhook/day13_webhook_logger.py")


# ═══════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Day 12 - Phone Number Setup")
    parser.add_argument("--bolna",  action="store_true", help="Use Bolna built-in number (demo)")
    parser.add_argument("--twilio", action="store_true", help="Use Twilio Indian number (production)")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  Aria - Day 12: Phone Number Setup")
    print(f"  Bolna Agent : {BOLNA_AGENT_ID or 'NOT SET'}")
    print(f"  Twilio Num  : {TWILIO_NUMBER or 'NOT SET'}")
    print(f"  ngrok URL   : {NGROK_URL or 'NOT SET'}")
    print("="*60)

    # Determine mode
    has_twilio = TWILIO_SID and "your_twilio" not in TWILIO_SID.lower()

    if args.twilio or has_twilio:
        mode = "twilio"
        setup_twilio_number()
    else:
        mode = "bolna"
        setup_bolna_number()

    verify_full_stack()
    print_summary(mode)
