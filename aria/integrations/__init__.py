"""
Aria Integrations Layer
========================
External service integrations:
  - Google Calendar → Appointment scheduling
  - Twilio          → WhatsApp, SMS, Voice notifications
"""

from aria.integrations.google_calendar import GoogleCalendarAgent
from aria.integrations.twilio_client import TwilioNotifier

__all__ = ["GoogleCalendarAgent", "TwilioNotifier"]
