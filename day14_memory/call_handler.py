"""
Day 14 — Unified Call Handler
==============================
Ties Redis (real-time) + Postgres (durable) into one call lifecycle manager.

Flow:
    1. Call starts  → Redis session created (fast)
    2. During call  → Redis updated each turn (real-time)
    3. Call ends    → Redis → Postgres (archive)
    4. Confirmation → Email/WhatsApp sent (n8n handles this via webhook)

This bridges your Bolna webhook (Day 13) with the memory layer (Day 14).
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional

from redis_manager import RedisSessionManager
from postgres_manager import PostgresManager


class UnifiedCallHandler:
    """
    Complete call lifecycle manager.

    Connects:
        - Bolna webhook payload (from Day 13)
        - Redis session (real-time state)
        - Postgres archive (durable history)
    """

    def __init__(self):
        self.redis    = RedisSessionManager()
        self.postgres = PostgresManager()

    def on_call_started(self, call_id: str, patient_phone: str) -> Dict:
        """
        Called when a call begins.
        Creates a Redis session for real-time tracking.
        """
        # Check if patient has called before
        history = self.postgres.get_patient_history(patient_phone, limit=1)
        is_returning = len(history) > 0

        session = self.redis.start_session(call_id, patient_phone)
        session["is_returning_patient"] = is_returning
        session["previous_calls"] = len(history)

        if is_returning:
            last = history[0]
            print(f"👤 Returning patient! Last call: {last['date']} | {last['treatment']}")
        else:
            print(f"🆕 New patient: {patient_phone}")

        return session

    def on_call_ended(self, bolna_payload: Dict) -> Dict:
        """
        Called when Bolna webhook fires after call ends.

        Processes the full Bolna payload (from Day 13 workflow),
        archives to Postgres, returns summary.

        Args:
            bolna_payload: The parsed output from n8n's 'Parse Bolna Payload' node
        """
        call_id      = bolna_payload.get("executionId", "unknown")
        patient_phone= bolna_payload.get("patientPhone", "")

        # Try to get active Redis session (if call was tracked)
        session = self.redis.get_session(call_id)

        if session:
            # Merge Bolna extracted data into session
            self.redis.update_session(call_id, {
                "state": "completed",
                "extracted_data": {
                    "patientName":       bolna_payload.get("patientName", ""),
                    "patientEmail":      bolna_payload.get("patientEmail", ""),
                    "bookingId":         bolna_payload.get("bookingId", ""),
                    "appointmentDate":   bolna_payload.get("appointmentDate", ""),
                    "appointmentTime":   bolna_payload.get("appointmentTime", ""),
                    "treatment":         bolna_payload.get("treatment", ""),
                    "language":          bolna_payload.get("language", "English"),
                    "summary":           bolna_payload.get("summary", ""),
                    "booking_status":    "confirmed" if bolna_payload.get("hasBooking") else "no_booking",
                }
            })
            # Archive Redis → Postgres
            final_session = self.redis.end_session(call_id)
        else:
            # No active Redis session (call started before handler was running)
            # Build a synthetic session from Bolna payload
            print(f"⚠️  No Redis session found for {call_id} — building from payload")
            final_session = {
                "call_id":      call_id,
                "patient_phone": patient_phone,
                "started_at":   bolna_payload.get("createdAt", datetime.utcnow().isoformat()),
                "ended_at":     bolna_payload.get("loggedAt", datetime.utcnow().isoformat()),
                "callStatus":   bolna_payload.get("callStatus", "completed"),
                "agentId":      bolna_payload.get("agentId", ""),
                "turns":        [],
                "extracted_data": {
                    "patientName":     bolna_payload.get("patientName", ""),
                    "patientEmail":    bolna_payload.get("patientEmail", ""),
                    "bookingId":       bolna_payload.get("bookingId", ""),
                    "appointmentDate": bolna_payload.get("appointmentDate", ""),
                    "appointmentTime": bolna_payload.get("appointmentTime", ""),
                    "treatment":       bolna_payload.get("treatment", ""),
                    "language":        bolna_payload.get("language", "English"),
                    "summary":         bolna_payload.get("summary", ""),
                    "booking_status":  "confirmed" if bolna_payload.get("hasBooking") else "no_booking",
                }
            }

        # Archive to Postgres
        self.postgres.save_call(final_session)

        # Prepare summary
        extracted = final_session.get("extracted_data", {})
        summary = {
            "call_id":    call_id,
            "patient":    extracted.get("patientName", patient_phone),
            "language":   extracted.get("language", "English"),
            "booking":    extracted.get("booking_status"),
            "booking_id": extracted.get("bookingId"),
            "date":       extracted.get("appointmentDate"),
            "time":       extracted.get("appointmentTime"),
            "treatment":  extracted.get("treatment"),
            "archived":   True,
        }
        print(f"✅ Call lifecycle complete: {json.dumps(summary, ensure_ascii=False)}")
        return summary

    def get_context_for_returning_patient(self, patient_phone: str) -> str:
        """
        Build a context string for the agent about a returning patient.
        Inject this into the Bolna agent's system prompt.
        """
        history = self.postgres.get_patient_history(patient_phone, limit=3)
        if not history:
            return ""

        lines = [f"RETURNING PATIENT CONTEXT (phone: {patient_phone}):"]
        for h in history:
            lines.append(f"  • {h['date']}: {h['treatment']} ({h['booking']})")

        last = history[0]
        if last.get("name"):
            lines.insert(1, f"Name: {last['name']}")

        return "\n".join(lines)


# ── Test ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Day 14 — Unified Call Handler Test")
    print("="*60)

    handler = UnifiedCallHandler()

    # Simulate a full call lifecycle
    test_call_id = "DEMO_UNIFIED_001"
    test_phone   = "+916302008804"

    # 1. Call starts
    print("\n📞 Step 1: Call starts...")
    handler.on_call_started(test_call_id, test_phone)

    # 2. Call ends with Bolna payload (simulating Day 13 output)
    print("\n📴 Step 2: Call ends (Bolna webhook fires)...")
    bolna_payload = {
        "executionId":    test_call_id,
        "agentId":        "aria-dental-v1",
        "callStatus":     "completed",
        "patientPhone":   test_phone,
        "patientName":    "లోకేష్ గడ్డం",
        "patientEmail":   "lokeshgaddam2514@gmail.com",
        "bookingId":      "BLN9999001",
        "appointmentDate": "రేపు ఉదయం",
        "appointmentTime": "10:00 AM",
        "treatment":      "Teeth Cleaning",
        "language":       "Telugu",
        "hasBooking":     True,
        "summary":        "Lokesh booked a teeth cleaning appointment for tomorrow 10 AM.",
        "createdAt":      datetime.utcnow().isoformat(),
        "loggedAt":       datetime.utcnow().isoformat(),
    }
    result = handler.on_call_ended(bolna_payload)

    # 3. Check returning patient context
    print("\n👤 Step 3: Returning patient context...")
    context = handler.get_context_for_returning_patient(test_phone)
    if context:
        print(context)
    else:
        print("(No previous calls found)")

    print("\n🎉 Day 14 complete! Redis + Postgres + Call Handler all working!\n")
