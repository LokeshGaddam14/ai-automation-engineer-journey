"""
Aria — Twilio Multi-Channel Notifier
======================================
Send booking confirmations via WhatsApp, SMS, and Voice calls.

Setup (FREE trial — no credit card needed for testing):
    1. Sign up at: https://www.twilio.com/
    2. Get Account SID + Auth Token from Console Dashboard
    3. Get a Twilio phone number (free with trial)
    4. For WhatsApp: Join sandbox at https://www.twilio.com/console/sms/whatsapp/sandbox
    5. Add to .env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER

What this does:
    - send_sms()                → Plain text SMS confirmation
    - send_whatsapp()           → WhatsApp message (rich formatting)
    - send_booking_confirmation() → Auto-chooses best channel
    - send_reminder()           → 24hr appointment reminder
    - send_cancellation()       → Cancellation notice
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass

# ── Config ─────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
CLINIC_NAME         = os.getenv("CLINIC_NAME", "Naveen Advanced Dental Clinic")
CLINIC_PHONE        = os.getenv("CLINIC_PHONE", "+91-XXXXXXXXXX")
CLINIC_ADDRESS      = os.getenv("CLINIC_ADDRESS", "123 Dental Street, Hyderabad")


class TwilioNotifier:
    """
    Multi-channel notification system for Aria.

    Supports:
        - SMS (plain text, works on all phones)
        - WhatsApp (rich formatting, attachments)
        - Graceful fallback to mock mode if Twilio not configured

    Usage:
        notifier = TwilioNotifier()
        notifier.send_booking_confirmation(
            phone="+916302008804",
            patient_name="Lokesh",
            date="2026-07-15",
            time="10:00",
            treatment="Teeth Cleaning",
            booking_id="BLN9999001"
        )
    """

    def __init__(self):
        self.client = None
        self._mock_mode = False
        self._init_client()

    def _init_client(self):
        """Initialize Twilio client or fall back to mock mode."""
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            print("[Twilio] No credentials found → MOCK MODE")
            self._mock_mode = True
            return

        try:
            from twilio.rest import Client
            self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            print("[Twilio] Client initialized ✅")
        except ImportError:
            print("[Twilio] twilio package not installed → MOCK MODE")
            print("         Install: pip install twilio")
            self._mock_mode = True

    # ── Core send methods ──────────────────────────────────────────────────────

    def send_sms(self, to_phone: str, message: str) -> Dict:
        """
        Send a plain SMS message.

        Args:
            to_phone: Recipient phone in E.164 format (+919876543210)
            message:  The text message body

        Returns: dict with sid, status, mock
        """
        if self._mock_mode:
            print(f"[Twilio MOCK] SMS → {to_phone}")
            print(f"  Message: {message[:100]}...")
            return {"status": "sent", "sid": "MOCK_SID_SMS", "mock": True, "channel": "sms"}

        try:
            msg = self.client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=to_phone
            )
            print(f"[Twilio] SMS sent → {to_phone} | SID: {msg.sid}")
            return {"status": "sent", "sid": msg.sid, "mock": False, "channel": "sms"}
        except Exception as e:
            print(f"[Twilio] SMS failed: {e}")
            return {"status": "failed", "error": str(e), "mock": False, "channel": "sms"}

    def send_whatsapp(self, to_phone: str, message: str) -> Dict:
        """
        Send a WhatsApp message via Twilio Sandbox.

        Note: Patient must have joined the sandbox first.
        Production WhatsApp requires Business API approval.

        Args:
            to_phone: Recipient phone in E.164 format
            message:  The WhatsApp message body (supports emoji)

        Returns: dict with sid, status, mock
        """
        # WhatsApp requires "whatsapp:" prefix
        wa_from = f"whatsapp:{TWILIO_PHONE_NUMBER}"
        wa_to   = f"whatsapp:{to_phone}"

        if self._mock_mode:
            print(f"[Twilio MOCK] WhatsApp → {to_phone}")
            print(f"  Message: {message[:100]}...")
            return {"status": "sent", "sid": "MOCK_SID_WA", "mock": True, "channel": "whatsapp"}

        try:
            msg = self.client.messages.create(
                body=message,
                from_=wa_from,
                to=wa_to
            )
            print(f"[Twilio] WhatsApp sent → {to_phone} | SID: {msg.sid}")
            return {"status": "sent", "sid": msg.sid, "mock": False, "channel": "whatsapp"}
        except Exception as e:
            print(f"[Twilio] WhatsApp failed: {e}")
            # Fallback to SMS
            print("[Twilio] Falling back to SMS...")
            return self.send_sms(to_phone, message)

    # ── High-level notification methods ───────────────────────────────────────

    def send_booking_confirmation(
        self,
        phone:        str,
        patient_name: str,
        date:         str,
        time:         str,
        treatment:    str = "Dental Appointment",
        booking_id:   str = "",
        channel:      str = "whatsapp"  # "whatsapp" | "sms" | "both"
    ) -> Dict:
        """
        Send appointment booking confirmation to patient.

        This is the main method called after a successful booking.

        Args:
            phone:        Patient's phone number (+919876543210)
            patient_name: Patient's name for personalization
            date:         Appointment date string
            time:         Appointment time string (HH:MM)
            treatment:    Type of dental treatment
            booking_id:   Booking reference number
            channel:      Notification channel

        Returns: dict with send results
        """
        message = self._build_confirmation_message(
            patient_name, date, time, treatment, booking_id
        )

        results = {}
        if channel in ("whatsapp", "both"):
            results["whatsapp"] = self.send_whatsapp(phone, message)
        if channel in ("sms", "both"):
            results["sms"] = self.send_sms(phone, message)
        if channel == "whatsapp":
            results = results.get("whatsapp", {})
        elif channel == "sms":
            results = results.get("sms", {})

        return results

    def send_reminder(
        self,
        phone:        str,
        patient_name: str,
        date:         str,
        time:         str,
        treatment:    str = "Dental Appointment",
        channel:      str = "whatsapp"
    ) -> Dict:
        """
        Send 24-hour appointment reminder.
        Typically called by a daily cron job or n8n scheduler.
        """
        message = (
            f"⏰ *Appointment Reminder* — {CLINIC_NAME}\n\n"
            f"Dear {patient_name},\n"
            f"This is a reminder for your appointment *tomorrow*:\n\n"
            f"📅 Date: {date}\n"
            f"🕐 Time: {time}\n"
            f"🦷 Treatment: {treatment}\n\n"
            f"📍 Address: {CLINIC_ADDRESS}\n"
            f"📞 Questions? Call: {CLINIC_PHONE}\n\n"
            f"_Please reply CONFIRM to confirm or CANCEL to cancel._"
        )

        if channel == "whatsapp":
            return self.send_whatsapp(phone, message)
        return self.send_sms(phone, message)

    def send_cancellation(
        self,
        phone:        str,
        patient_name: str,
        date:         str,
        time:         str,
        channel:      str = "whatsapp"
    ) -> Dict:
        """Send appointment cancellation notice."""
        message = (
            f"❌ *Appointment Cancelled* — {CLINIC_NAME}\n\n"
            f"Dear {patient_name},\n"
            f"Your appointment on {date} at {time} has been cancelled.\n\n"
            f"To rebook, call us at {CLINIC_PHONE} or reply to this message.\n\n"
            f"We apologize for any inconvenience."
        )

        if channel == "whatsapp":
            return self.send_whatsapp(phone, message)
        return self.send_sms(phone, message)

    def send_emergency_alert(self, phone: str, patient_name: str) -> Dict:
        """
        Send emergency slot availability alert.
        Used when patient reports severe pain/dental emergency.
        """
        message = (
            f"🚨 *Emergency Dental Slot Available* — {CLINIC_NAME}\n\n"
            f"Dear {patient_name},\n"
            f"We have an emergency appointment available for you today.\n\n"
            f"Please call us immediately at {CLINIC_PHONE} or come directly to:\n"
            f"📍 {CLINIC_ADDRESS}\n\n"
            f"_Our dentist is ready to see you as soon as possible._"
        )
        return self.send_whatsapp(phone, message)

    # ── Message builders ──────────────────────────────────────────────────────

    def _build_confirmation_message(
        self,
        patient_name: str,
        date:         str,
        time:         str,
        treatment:    str,
        booking_id:   str
    ) -> str:
        """Build a formatted booking confirmation message."""
        booking_ref = f"\n📋 Booking ID: `{booking_id}`" if booking_id else ""
        return (
            f"✅ *Appointment Confirmed!* — {CLINIC_NAME}\n\n"
            f"Dear {patient_name},\n"
            f"Your appointment has been successfully booked.\n\n"
            f"📅 Date: {date}\n"
            f"🕐 Time: {time}\n"
            f"🦷 Treatment: {treatment}"
            f"{booking_ref}\n\n"
            f"📍 Address: {CLINIC_ADDRESS}\n"
            f"📞 Contact: {CLINIC_PHONE}\n\n"
            f"_Please arrive 10 minutes early. Bring any previous dental records._\n\n"
            f"To reschedule or cancel, call us at {CLINIC_PHONE}.\n"
            f"Thank you for choosing {CLINIC_NAME}! 😊"
        )
