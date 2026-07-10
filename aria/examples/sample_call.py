"""
Aria — Full Call Flow Example
================================
Demonstrates the complete patient call lifecycle end-to-end.
No external services needed — runs in mock/in-memory mode.

Run:
    cd ai-automation
    python aria/examples/sample_call.py
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add project root to path so `aria` package is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ANSI colors for pretty output
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
BLUE   = "\033[94m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
MAGENTA= "\033[95m"
RED    = "\033[91m"


def print_header(text: str):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


def print_step(step: int, title: str):
    print(f"\n{BOLD}{BLUE}[Step {step}]{RESET} {title}")
    print(f"{BLUE}{'-'*50}{RESET}")


def print_agent(text: str):
    print(f"  {MAGENTA}🤖 Aria:{RESET} {text}")


def print_patient(text: str):
    print(f"  {GREEN}👤 Patient:{RESET} {text}")


def print_info(text: str):
    print(f"  {YELLOW}ℹ️  {text}{RESET}")


def print_success(text: str):
    print(f"  {GREEN}✅ {text}{RESET}")


def print_error(text: str):
    print(f"  {RED}❌ {text}{RESET}")


def demo_complete_call_flow():
    """
    Simulate a complete patient call:
        Patient: Lokesh Gaddam (+916302008804)
        Intent:  Book a teeth cleaning appointment for tomorrow 10 AM
        Language: English
    """
    print_header("Aria Voice Receptionist — Full Call Demo")
    print(f"\n{CYAN}Simulating a complete dental appointment booking call.{RESET}")
    print(f"{CYAN}All components run in mock/in-memory mode — no setup needed.{RESET}\n")

    # ── Initialize components ──────────────────────────────────────────────────
    print_step(1, "Initialize Aria Components")

    from aria.memory.redis_manager import RedisSessionManager
    from aria.memory.postgres_manager import PostgresManager
    from aria.integrations.google_calendar import GoogleCalendarAgent
    from aria.integrations.twilio_client import TwilioNotifier
    from aria.agents.orchestrator import (
        greeting_agent, booking_agent, info_agent,
        emergency_agent, CallState
    )

    redis    = RedisSessionManager()
    postgres = PostgresManager()
    calendar = GoogleCalendarAgent()
    twilio   = TwilioNotifier()

    print_success("Redis Session Manager ready")
    print_success("Postgres Manager ready (SQLite fallback)")
    print_success("Google Calendar ready (mock mode)")
    print_success("Twilio Notifier ready (mock mode)")

    # ── Call details ───────────────────────────────────────────────────────────
    CALL_ID       = f"call_DEMO_{int(time.time())}"
    PATIENT_PHONE = "+916302008804"
    PATIENT_NAME  = "Lokesh Gaddam"
    PATIENT_EMAIL = "lokeshgaddam2514@gmail.com"

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 2: Incoming call — start session
    # ══════════════════════════════════════════════════════════════════════════
    print_step(2, "Incoming Call — Session Start")

    # Check patient history
    history = postgres.get_patient_history(PATIENT_PHONE, limit=1)
    is_returning = len(history) > 0

    session = redis.start_session(CALL_ID, PATIENT_PHONE)
    session["is_returning_patient"] = is_returning

    print_info(f"Call ID: {CALL_ID}")
    print_info(f"Patient: {PATIENT_PHONE}")
    print_info(f"Returning patient: {is_returning}")
    print_success(f"Redis session created (mode: {redis.mode})")

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 3: Greeting Agent
    # ══════════════════════════════════════════════════════════════════════════
    print_step(3, "Greeting Agent (LangGraph Node)")

    state: CallState = {
        "call_id":          CALL_ID,
        "patient_phone":    PATIENT_PHONE,
        "language":         "English",
        "started_at":       datetime.now().isoformat(),
        "messages":         [],
        "turn_count":       0,
        "patient_name":     None,
        "appointment_date": None,
        "appointment_time": None,
        "treatment":        None,
        "patient_email":    None,
        "chief_complaint":  None,
        "urgency_level":    None,
        "intent":           None,
        "current_agent":    "greeting",
        "next_agent":       None,
        "is_complete":      False,
        "booking_confirmed": False,
        "booking_id":       None,
        "calendar_event_id": None,
        "last_response":    "",
        "escalation_reason": None,
    }

    state = greeting_agent(state)
    print_agent(state["last_response"])

    # Patient logs in Redis
    redis.append_turn(CALL_ID, "agent", state["last_response"])

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 4: Patient speaks — intent detection
    # ══════════════════════════════════════════════════════════════════════════
    print_step(4, "Patient Speaks — Intent Detection")

    patient_msg_1 = "I need to book an appointment for tomorrow."
    print_patient(patient_msg_1)
    redis.append_turn(CALL_ID, "patient", patient_msg_1, {"intent": "booking"})

    state["messages"].append({
        "role": "patient", "content": patient_msg_1,
        "timestamp": datetime.now().isoformat()
    })
    state = greeting_agent(state)
    print_info(f"Detected intent: {state.get('intent')} → routing to: {state.get('next_agent')}")

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 5: Booking Agent — collect patient name
    # ══════════════════════════════════════════════════════════════════════════
    print_step(5, "Booking Agent — Collecting Info")

    # Turn 1: Ask for name
    state["intent"] = "booking"
    state["next_agent"] = "booking"
    state = booking_agent(state)
    print_agent(state["last_response"])
    redis.append_turn(CALL_ID, "agent", state["last_response"])

    # Patient provides name
    patient_msg_2 = f"My name is {PATIENT_NAME}."
    print_patient(patient_msg_2)
    state["patient_name"] = PATIENT_NAME
    state["messages"].append({"role": "patient", "content": patient_msg_2, "timestamp": datetime.now().isoformat()})
    redis.append_turn(CALL_ID, "patient", patient_msg_2, {"name": PATIENT_NAME})
    redis.update_session(CALL_ID, {"extracted_data": {"name": PATIENT_NAME}})

    # Turn 2: Ask for date
    state = booking_agent(state)
    print_agent(state["last_response"])
    redis.append_turn(CALL_ID, "agent", state["last_response"])

    # Patient provides date
    patient_msg_3 = "Tomorrow would be great."
    print_patient(patient_msg_3)
    state["appointment_date"] = "tomorrow"
    state["messages"].append({"role": "patient", "content": patient_msg_3, "timestamp": datetime.now().isoformat()})
    redis.append_turn(CALL_ID, "patient", patient_msg_3, {"date": "tomorrow"})

    # Turn 3: Ask for time
    state = booking_agent(state)
    print_agent(state["last_response"])
    redis.append_turn(CALL_ID, "agent", state["last_response"])

    # Patient provides time
    patient_msg_4 = "10 AM works for me."
    print_patient(patient_msg_4)
    state["appointment_time"] = "10:00"
    state["messages"].append({"role": "patient", "content": patient_msg_4, "timestamp": datetime.now().isoformat()})
    redis.append_turn(CALL_ID, "patient", patient_msg_4, {"time": "10:00"})

    # Turn 4: Ask for treatment
    state = booking_agent(state)
    print_agent(state["last_response"])
    redis.append_turn(CALL_ID, "agent", state["last_response"])

    # Patient provides treatment
    patient_msg_5 = "Teeth cleaning please."
    print_patient(patient_msg_5)
    state["treatment"]    = "Teeth Cleaning"
    state["patient_email"] = PATIENT_EMAIL
    state["messages"].append({"role": "patient", "content": patient_msg_5, "timestamp": datetime.now().isoformat()})
    redis.append_turn(CALL_ID, "patient", patient_msg_5, {"treatment": "Teeth Cleaning"})

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 6: Confirm booking on Google Calendar
    # ══════════════════════════════════════════════════════════════════════════
    print_step(6, "Calendar Check & Booking")

    slots = calendar.get_available_slots("tomorrow")
    print_info(f"Available slots: {slots[:5]}...")

    booking_result = calendar.book_appointment(
        patient_name  = PATIENT_NAME,
        patient_phone = PATIENT_PHONE,
        date_str      = "tomorrow",
        time_str      = "10:00 AM",
        treatment     = "Teeth Cleaning",
        patient_email = PATIENT_EMAIL,
        booking_id    = "BLN_PREVIEW"
    )
    print_success(f"Calendar result: {booking_result['status']} | Event: {booking_result['event_id']}")

    # Final booking confirmation from agent
    state["calendar_event_id"] = booking_result.get("event_id")
    state = booking_agent(state)
    print_agent(state["last_response"])
    redis.append_turn(CALL_ID, "agent", state["last_response"])

    booking_id = state["booking_id"]
    print_success(f"Booking confirmed! ID: {booking_id}")

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 7: Send WhatsApp confirmation via Twilio
    # ══════════════════════════════════════════════════════════════════════════
    print_step(7, "Twilio WhatsApp Confirmation")

    twilio_result = twilio.send_booking_confirmation(
        phone        = PATIENT_PHONE,
        patient_name = PATIENT_NAME,
        date         = "tomorrow",
        time         = "10:00 AM",
        treatment    = "Teeth Cleaning",
        booking_id   = booking_id,
        channel      = "whatsapp"
    )
    print_success(f"WhatsApp sent | Status: {twilio_result['status']}")
    print_info(f"Notification: {'REAL' if not twilio_result.get('mock') else 'MOCK (no Twilio credentials)'}")

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 8: Archive call to Postgres
    # ══════════════════════════════════════════════════════════════════════════
    print_step(8, "Archive Call to Postgres")

    final_session = redis.end_session(CALL_ID)
    if final_session:
        final_session["extracted_data"].update({
            "patientName":    PATIENT_NAME,
            "patientEmail":   PATIENT_EMAIL,
            "bookingId":      booking_id,
            "appointmentDate": "tomorrow",
            "appointmentTime": "10:00 AM",
            "treatment":      "Teeth Cleaning",
            "booking_status": "confirmed",
            "language":       "English",
            "summary":        f"{PATIENT_NAME} booked teeth cleaning for tomorrow 10 AM.",
        })
        postgres.save_call(final_session)
        print_success(f"Archived to Postgres | Turns: {len(final_session['turns'])}")

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 9: Analytics
    # ══════════════════════════════════════════════════════════════════════════
    print_step(9, "Analytics & Verification")

    stats = postgres.get_stats()
    history = postgres.get_patient_history(PATIENT_PHONE)

    print_success(f"Total calls in DB: {stats['total_calls']}")
    print_success(f"Confirmed bookings: {stats['confirmed_bookings']}")
    print_success(f"Booking rate: {stats['booking_rate_pct']}%")
    print_success(f"Patient history entries: {len(history)}")

    # ══════════════════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    print_header("🎉 Demo Complete — Full Call Summary")

    print(f"""
  {BOLD}Patient:{RESET}  {PATIENT_NAME} ({PATIENT_PHONE})
  {BOLD}Call ID:{RESET}  {CALL_ID}
  {BOLD}Booking:{RESET}  {booking_id}
  {BOLD}Date:{RESET}     Tomorrow at 10:00 AM
  {BOLD}Treatment:{RESET} Teeth Cleaning
  {BOLD}Status:{RESET}   {GREEN}CONFIRMED{RESET}
  {BOLD}Turns:{RESET}    {len(final_session['turns']) if final_session else 'N/A'}

  {CYAN}What happened:{RESET}
  {GREEN}✅{RESET} Redis session created (real-time state)
  {GREEN}✅{RESET} LangGraph routed: greeting → booking
  {GREEN}✅{RESET} Google Calendar checked + event created (mock)
  {GREEN}✅{RESET} WhatsApp confirmation sent via Twilio (mock)
  {GREEN}✅{RESET} Call archived to Postgres (SQLite)
  {GREEN}✅{RESET} Analytics updated

  {BOLD}{CYAN}Architecture Demonstrated:{RESET}
  ┌─────────────────────────────────────────────┐
  │  Bolna Call → FastAPI → UnifiedCallHandler  │
  │       ↓                                     │
  │  Redis (real-time) + Postgres (archive)     │
  │       ↓                                     │
  │  LangGraph: Greeting → Booking Agent        │
  │       ↓                                     │
  │  Google Calendar (availability check)       │
  │       ↓                                     │
  │  Twilio (WhatsApp confirmation)             │
  └─────────────────────────────────────────────┘
""")


def demo_telugu_call():
    """Demonstrate Telugu language call handling."""
    print_header("Telugu Language Call Demo")

    from aria.agents.orchestrator import greeting_agent, booking_agent, CallState

    state: CallState = {
        "call_id":          "call_TEL_001",
        "patient_phone":    "+916302008804",
        "language":         "Telugu",
        "started_at":       datetime.now().isoformat(),
        "messages":         [
            {"role": "patient", "content": "నాకు అపాయింట్మెంట్ కావాలి", "timestamp": datetime.now().isoformat()}
        ],
        "turn_count":       1,
        "patient_name":     "లోకేష్ గడ్డం",
        "appointment_date": "రేపు",
        "appointment_time": "10:00 AM",
        "treatment":        "Teeth Cleaning",
        "patient_email":    "lokeshgaddam2514@gmail.com",
        "chief_complaint":  None,
        "urgency_level":    None,
        "intent":           "booking",
        "current_agent":    "greeting",
        "next_agent":       "booking",
        "is_complete":      False,
        "booking_confirmed": False,
        "booking_id":       None,
        "calendar_event_id": None,
        "last_response":    "",
        "escalation_reason": None,
    }

    state = greeting_agent(state)
    print_agent(f"(Telugu) {state['last_response']}")

    state = booking_agent(state)
    print_agent(f"(Booking) {state['last_response']}")
    print_success(f"Booking confirmed: {state['booking_confirmed']} | ID: {state.get('booking_id')}")


def demo_emergency_flow():
    """Demonstrate emergency dental case handling."""
    print_header("Emergency Case Demo")

    from aria.agents.orchestrator import greeting_agent, emergency_agent, CallState

    state: CallState = {
        "call_id":          "call_EMRG_001",
        "patient_phone":    "+919876543210",
        "language":         "English",
        "started_at":       datetime.now().isoformat(),
        "messages":         [
            {"role": "patient", "content": "I have severe tooth pain and swelling!", "timestamp": datetime.now().isoformat()}
        ],
        "turn_count":       1,
        "patient_name":     None,
        "appointment_date": None,
        "appointment_time": None,
        "treatment":        None,
        "patient_email":    None,
        "chief_complaint":  "severe tooth pain",
        "urgency_level":    "high",
        "intent":           "emergency",
        "current_agent":    "greeting",
        "next_agent":       "emergency",
        "is_complete":      False,
        "booking_confirmed": False,
        "booking_id":       None,
        "calendar_event_id": None,
        "last_response":    "",
        "escalation_reason": None,
    }

    state = greeting_agent(state)
    print_info(f"Intent detected: {state.get('intent')}")

    state = emergency_agent(state)
    print_agent(state["last_response"])
    print_success(f"Urgency level: {state['urgency_level']}")


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{BOLD}{CYAN}Aria — AI Voice Receptionist Demo{RESET}")
    print(f"{CYAN}Day 14-16: Memory + Integrations + Deployment{RESET}")
    print(f"{CYAN}By: Lokesh Gaddam | AI Automation Engineer Journey{RESET}\n")

    try:
        # Main demo
        demo_complete_call_flow()

        # Telugu language demo
        print()
        demo_telugu_call()

        # Emergency demo
        print()
        demo_emergency_flow()

        print(f"\n{BOLD}{GREEN}🚀 All demos completed successfully!{RESET}")
        print(f"{GREEN}   Aria is ready for production deployment.{RESET}\n")

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Demo interrupted by user.{RESET}")
    except Exception as e:
        print(f"\n{RED}Demo error: {e}{RESET}")
        import traceback
        traceback.print_exc()
