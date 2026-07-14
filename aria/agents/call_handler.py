"""
Aria — Unified Call Handler
=============================
Ties Redis (real-time) + Postgres (durable) + LangGraph into one call lifecycle manager.

Flow:
    1. Call starts  → Redis session created (fast)
    2. During call  → Redis updated each turn + LangGraph routes agent
    3. Call ends    → Redis → Postgres (archive)
    4. Confirmation → Twilio WhatsApp/SMS sent
"""

import json
import os
import random
from datetime import datetime
from typing import Dict, Optional

from aria.memory.redis_manager import RedisSessionManager
from aria.memory.postgres_manager import PostgresManager


class UnifiedCallHandler:
    """
    Complete call lifecycle manager for Aria.

    Connects:
        - Bolna webhook payload (incoming call data)
        - Redis session (real-time state during call)
        - Postgres archive (durable history after call)
        - LangGraph orchestrator (agent routing)
        - Twilio notifier (confirmations)
    """

    def __init__(self):
        self.redis    = RedisSessionManager()
        self.postgres = PostgresManager()

    def start_call(self, call_id: str, patient_phone: str) -> Dict:
        """
        Called when a call begins.
        Creates Redis session + checks patient history.

        Returns: session dict with patient context
        """
        # Check if patient has called before
        history = self.postgres.get_patient_history(patient_phone, limit=1)
        is_returning = len(history) > 0

        session = self.redis.start_session(call_id, patient_phone)
        session["is_returning_patient"] = is_returning
        session["previous_calls"] = len(history)

        if is_returning:
            last = history[0]
            print(f"👤 Returning patient! Last: {last['date']} | {last['treatment']}")
        else:
            print(f"🆕 New patient: {patient_phone}")

        return session

    def process_turn(
        self,
        call_id:        str,
        patient_input:  str,
        extracted_data: Optional[Dict] = None
    ) -> Dict:
        """
        Process one conversation turn.

        Args:
            call_id:        Active call identifier
            patient_input:  What the patient said
            extracted_data: Any data extracted from this turn

        Returns: dict with agent response and updated state
        """
        # Log patient turn
        self.redis.append_turn(call_id, "patient", patient_input, extracted_data)

        # Update extracted data if provided
        if extracted_data:
            self.redis.update_session(call_id, {"extracted_data": extracted_data})

        # Get current session
        session = self.redis.get_session(call_id)
        if not session:
            return {"error": f"Session {call_id} not found", "response": "I'm sorry, I've lost track of our conversation. Could you start again?"}

        # Route through LangGraph orchestrator
        try:
            from aria.agents.orchestrator import build_aria_graph, CallState
            graph = build_aria_graph()

            if graph:
                state: CallState = {
                    "call_id":          call_id,
                    "patient_phone":    session["patient_phone"],
                    "language":         extracted_data.get("language", "English") if extracted_data else "English",
                    "started_at":       session["started_at"],
                    "messages":         [{"role": "patient", "content": patient_input, "timestamp": datetime.now().isoformat()}],
                    "turn_count":       len(session["turns"]),
                    "patient_name":     session["extracted_data"].get("name"),
                    "appointment_date": session["extracted_data"].get("appointment_date"),
                    "appointment_time": session["extracted_data"].get("appointment_time"),
                    "treatment":        session["extracted_data"].get("treatment"),
                    "patient_email":    session["extracted_data"].get("email"),
                    "chief_complaint":  None,
                    "urgency_level":    None,
                    "intent":           None,
                    "current_agent":    session.get("state", "greeting"),
                    "next_agent":       None,
                    "is_complete":      False,
                    "booking_confirmed": False,
                    "booking_id":       None,
                    "calendar_event_id": None,
                    "last_response":    "",
                    "escalation_reason": None,
                }

                result = graph.invoke(state)
                agent_response = result.get("last_response", "I understand. How can I help you?")
                booking_confirmed = result.get("booking_confirmed", False)
                booking_id = result.get("booking_id")

                # Update Redis with orchestrator results
                update = {"state": result.get("current_agent", "booking")}
                if booking_confirmed:
                    update["extracted_data"] = {
                        "booking_status": "confirmed",
                        "booking_id": booking_id,
                    }
                self.redis.update_session(call_id, update)

                # Log agent response
                self.redis.append_turn(call_id, "agent", agent_response)

                return {
                    "response":          agent_response,
                    "booking_confirmed": booking_confirmed,
                    "booking_id":        booking_id,
                    "current_agent":     result.get("current_agent"),
                    "is_complete":       result.get("is_complete", False),
                }

        except Exception as e:
            print(f"[CallHandler] Orchestrator error: {e}")

        # Simple fallback response
        fallback = "I understand. Could you please repeat that?"
        self.redis.append_turn(call_id, "agent", fallback)
        return {"response": fallback, "booking_confirmed": False}

    def end_call(self, call_id: str, bolna_payload: Optional[Dict] = None) -> Dict:
        """
        Called when a call ends.

        Processes Bolna payload (if provided), archives to Postgres,
        optionally sends Twilio confirmation.

        Args:
            call_id:       The call identifier
            bolna_payload: Optional Bolna webhook payload

        Returns: Summary dict
        """
        # Merge Bolna payload into Redis session if provided
        if bolna_payload:
            try:
                self.redis.update_session(call_id, {
                    "state": "completed",
                    "extracted_data": {
                        "patientName":    bolna_payload.get("patientName", ""),
                        "patientEmail":   bolna_payload.get("patientEmail", ""),
                        "bookingId":      bolna_payload.get("bookingId", ""),
                        "appointmentDate": bolna_payload.get("appointmentDate", ""),
                        "appointmentTime": bolna_payload.get("appointmentTime", ""),
                        "treatment":      bolna_payload.get("treatment", ""),
                        "language":       bolna_payload.get("language", "English"),
                        "summary":        bolna_payload.get("summary", ""),
                        "booking_status": "confirmed" if bolna_payload.get("hasBooking") else "no_booking",
                    }
                })
            except Exception:
                pass

        # End Redis session
        final_session = self.redis.end_session(call_id)

        if not final_session and bolna_payload:
            # Build synthetic session from payload
            final_session = {
                "call_id":       call_id,
                "patient_phone": bolna_payload.get("patientPhone", ""),
                "started_at":    bolna_payload.get("createdAt", datetime.utcnow().isoformat()),
                "ended_at":      bolna_payload.get("loggedAt", datetime.utcnow().isoformat()),
                "callStatus":    bolna_payload.get("callStatus", "completed"),
                "agentId":       bolna_payload.get("agentId", ""),
                "turns":         [],
                "extracted_data": {
                    "patientName":    bolna_payload.get("patientName", ""),
                    "patientEmail":   bolna_payload.get("patientEmail", ""),
                    "bookingId":      bolna_payload.get("bookingId", ""),
                    "appointmentDate": bolna_payload.get("appointmentDate", ""),
                    "appointmentTime": bolna_payload.get("appointmentTime", ""),
                    "treatment":      bolna_payload.get("treatment", ""),
                    "language":       bolna_payload.get("language", "English"),
                    "summary":        bolna_payload.get("summary", ""),
                    "booking_status": "confirmed" if bolna_payload.get("hasBooking") else "no_booking",
                }
            }
        elif not final_session:
            return {"error": f"Session {call_id} not found"}

        # Archive to Postgres
        self.postgres.save_call(final_session)

        # Send Twilio confirmation if booking was made
        extracted = final_session.get("extracted_data", {})
        if extracted.get("booking_status") == "confirmed":
            phone = final_session.get("patient_phone", "")
            if phone:
                try:
                    from aria.integrations.twilio_client import TwilioNotifier
                    notifier = TwilioNotifier()
                    notifier.send_booking_confirmation(
                        phone        = phone,
                        patient_name = extracted.get("patientName", "Patient"),
                        date         = extracted.get("appointmentDate", ""),
                        time         = extracted.get("appointmentTime", ""),
                        treatment    = extracted.get("treatment", "Dental Appointment"),
                        booking_id   = extracted.get("bookingId", ""),
                    )
                except Exception as e:
                    print(f"[CallHandler] Twilio notification failed: {e}")

        summary = {
            "call_id":    call_id,
            "patient":    extracted.get("patientName", final_session.get("patient_phone")),
            "language":   extracted.get("language", "English"),
            "booking":    extracted.get("booking_status"),
            "booking_id": extracted.get("bookingId"),
            "date":       extracted.get("appointmentDate"),
            "time":       extracted.get("appointmentTime"),
            "treatment":  extracted.get("treatment"),
            "archived":   True,
        }
        print(f"[OK] Call lifecycle complete: {json.dumps(summary, ensure_ascii=False)}")
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
