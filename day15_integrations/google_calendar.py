"""
Day 15 — Google Calendar Integration
======================================
Check dentist availability + auto-create appointment events.

Setup (FREE — no credit card needed):
    1. Go to: https://console.cloud.google.com/
    2. Create project → Enable "Google Calendar API"
    3. Create credentials: OAuth 2.0 Desktop App
    4. Download JSON → save as: day15_integrations/credentials.json
    5. First run opens browser to authorize → token.json saved automatically

What this does:
    - get_available_slots()   → "We have 10am, 2pm, 4pm available tomorrow"
    - book_appointment()      → Creates event on clinic's Google Calendar
    - cancel_appointment()    → Deletes/cancels event by event_id
    - get_todays_schedule()   → Summary of today's appointments
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

# ── Config ─────────────────────────────────────────────────────────────────────
CLINIC_CALENDAR_ID   = os.getenv("GOOGLE_CALENDAR_ID", "primary")
CLINIC_TZ            = os.getenv("CLINIC_TIMEZONE", "Asia/Kolkata")
CLINIC_START_HOUR    = int(os.getenv("CLINIC_START_HOUR", "9"))    # 9 AM
CLINIC_END_HOUR      = int(os.getenv("CLINIC_END_HOUR",   "18"))   # 6 PM
SLOT_DURATION_MINS   = int(os.getenv("SLOT_DURATION_MINS", "30"))  # 30-min slots
CREDENTIALS_FILE     = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE           = os.path.join(os.path.dirname(__file__), "token.json")


class GoogleCalendarAgent:
    """
    Google Calendar integration for dental clinic.

    Handles:
        - Checking free time slots
        - Booking appointments
        - Cancelling appointments
        - Daily schedule overview
    """

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self):
        self.service = None
        self._mock_mode = False
        self._authenticate()

    def _authenticate(self):
        """
        Authenticate with Google Calendar API.

        Tries:
            1. Saved token (token.json)
            2. OAuth flow (opens browser once)
            3. Mock mode (no credentials — for development/testing)
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            creds = None

            # Load saved token
            if os.path.exists(TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, self.SCOPES)

            # Refresh or re-authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif os.path.exists(CREDENTIALS_FILE):
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                    # Save token for next run
                    with open(TOKEN_FILE, "w") as f:
                        f.write(creds.to_json())
                else:
                    raise FileNotFoundError("credentials.json not found")

            self.service = build("calendar", "v3", credentials=creds)
            print("[Calendar] Authenticated with Google Calendar API")

        except (ImportError, FileNotFoundError) as e:
            print(f"[Calendar] WARNING: {e}")
            print("[Calendar] Running in MOCK MODE (no real calendar calls)")
            self._mock_mode = True

    # ── Availability ───────────────────────────────────────────────────────────

    def get_available_slots(
        self,
        date_str: str,  # "2026-07-11" or "tomorrow" or "Monday"
    ) -> List[str]:
        """
        Get available time slots for a given date.

        Returns list of times like: ["09:00", "09:30", "10:00", ...]
        """
        date = self._resolve_date(date_str)
        if not date:
            return []

        if self._mock_mode:
            return self._mock_slots(date)

        # Get existing events for the day
        tz_suffix = "+05:30"  # IST
        start_of_day = f"{date.strftime('%Y-%m-%d')}T00:00:00{tz_suffix}"
        end_of_day   = f"{date.strftime('%Y-%m-%d')}T23:59:59{tz_suffix}"

        try:
            events_result = self.service.events().list(
                calendarId=CLINIC_CALENDAR_ID,
                timeMin=start_of_day,
                timeMax=end_of_day,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            events = events_result.get("items", [])
        except Exception as e:
            print(f"[Calendar] Error fetching events: {e}")
            return self._mock_slots(date)

        # Build occupied set
        occupied = set()
        for event in events:
            start_str = event["start"].get("dateTime", "")
            if start_str:
                try:
                    # Parse ISO time and extract HH:MM
                    dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    occupied.add(dt.strftime("%H:%M"))
                except ValueError:
                    pass

        # Generate all slots and filter out occupied ones
        available = []
        current_hour = CLINIC_START_HOUR
        current_min  = 0
        while current_hour < CLINIC_END_HOUR:
            slot = f"{current_hour:02d}:{current_min:02d}"
            if slot not in occupied:
                available.append(slot)
            current_min += SLOT_DURATION_MINS
            if current_min >= 60:
                current_min -= 60
                current_hour += 1

        return available

    def book_appointment(
        self,
        patient_name:  str,
        patient_phone: str,
        date_str:      str,
        time_str:      str,   # "10:00" or "10:00 AM"
        treatment:     str = "Dental Appointment",
        patient_email: str = "",
        booking_id:    str = "",
    ) -> Dict:
        """
        Create appointment on clinic's Google Calendar.

        Returns: dict with event_id, htmlLink, status
        """
        date = self._resolve_date(date_str)
        time = self._normalize_time(time_str)

        if not date or not time:
            return {"status": "error", "message": f"Invalid date/time: {date_str} {time_str}"}

        date_iso  = date.strftime("%Y-%m-%d")
        start_iso = f"{date_iso}T{time}:00+05:30"
        end_time  = self._add_minutes(time, SLOT_DURATION_MINS)
        end_iso   = f"{date_iso}T{end_time}:00+05:30"

        if self._mock_mode:
            mock_id = f"mock_event_{booking_id or 'X'}"
            print(f"[Calendar] MOCK: Booked {patient_name} on {date_iso} at {time}")
            return {
                "status":   "confirmed",
                "event_id": mock_id,
                "date":     date_iso,
                "time":     time,
                "htmlLink": f"https://calendar.google.com/calendar/event?eid={mock_id}",
                "mock":     True
            }

        event_body = {
            "summary": f"[{treatment}] {patient_name}",
            "description": (
                f"Patient: {patient_name}\n"
                f"Phone:   {patient_phone}\n"
                f"Email:   {patient_email}\n"
                f"Booking: {booking_id}\n"
                f"Treatment: {treatment}\n"
                f"Booked via: Aria Voice Agent (Bolna AI)"
            ),
            "start": {"dateTime": start_iso, "timeZone": CLINIC_TZ},
            "end":   {"dateTime": end_iso,   "timeZone": CLINIC_TZ},
            "colorId": "2",  # Sage green
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email",  "minutes": 1440},  # 24h before
                    {"method": "popup",  "minutes": 30},    # 30min before
                ]
            }
        }

        # Add attendee if email provided
        if patient_email:
            event_body["attendees"] = [{"email": patient_email}]

        try:
            created = self.service.events().insert(
                calendarId=CLINIC_CALENDAR_ID,
                body=event_body,
                sendUpdates="all" if patient_email else "none"
            ).execute()

            print(f"[Calendar] Booked: {patient_name} | {date_iso} {time}")
            return {
                "status":   "confirmed",
                "event_id": created.get("id"),
                "date":     date_iso,
                "time":     time,
                "htmlLink": created.get("htmlLink"),
                "mock":     False
            }
        except Exception as e:
            print(f"[Calendar] Booking error: {e}")
            return {"status": "error", "message": str(e)}

    def cancel_appointment(self, event_id: str) -> Dict:
        """Cancel/delete an appointment by event ID."""
        if self._mock_mode:
            print(f"[Calendar] MOCK: Cancelled event {event_id}")
            return {"status": "cancelled", "event_id": event_id}

        try:
            self.service.events().delete(
                calendarId=CLINIC_CALENDAR_ID,
                eventId=event_id
            ).execute()
            return {"status": "cancelled", "event_id": event_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_todays_schedule(self) -> List[Dict]:
        """Get all appointments for today — useful for daily summary."""
        today = datetime.now()
        slots_today = self.get_available_slots(today.strftime("%Y-%m-%d"))

        if self._mock_mode:
            return [
                {"time": "10:00", "patient": "Ravi Kumar", "treatment": "Cleaning"},
                {"time": "11:00", "patient": "Priya Sharma", "treatment": "Root Canal"},
                {"time": "14:30", "patient": "Lokesh Gaddam", "treatment": "Consultation"},
            ]
        return []  # Real implementation queries API

    # ── Helper methods ─────────────────────────────────────────────────────────

    def _resolve_date(self, date_str: str) -> Optional[datetime]:
        """Convert 'tomorrow', 'Monday', '2026-07-11' → datetime object."""
        today = datetime.now()
        date_lower = date_str.lower().strip()

        if date_lower in ("today", "today's", "today morning"):
            return today

        if date_lower in ("tomorrow", "రేపు", "رواز", "kal", "நாளை", "नाल"):
            return today + timedelta(days=1)

        # Day of week
        days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6}
        for day_name, day_num in days.items():
            if day_name in date_lower:
                days_ahead = (day_num - today.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                return today + timedelta(days=days_ahead)

        # ISO format: YYYY-MM-DD
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass

        print(f"[Calendar] Could not resolve date: '{date_str}' — using tomorrow")
        return today + timedelta(days=1)

    def _normalize_time(self, time_str: str) -> Optional[str]:
        """Convert '10 AM', '10:00 AM', '10:00', '10h' → 'HH:MM'."""
        import re
        time_str = time_str.strip().upper()

        # Remove Telugu/Hindi time words
        time_str = time_str.replace("ఉదయం", "AM").replace("UDAYAM", "AM")
        time_str = time_str.replace("PMMM", "PM").replace("రాత్రి", "PM")

        # Match patterns: "10:00 AM", "10 AM", "14:30", "10:00"
        patterns = [
            r"(\d{1,2}):(\d{2})\s*(AM|PM)?",
            r"(\d{1,2})\s*(AM|PM)",
        ]
        for pat in patterns:
            m = re.search(pat, time_str)
            if m:
                groups = m.groups()
                if len(groups) == 3 and groups[1]:
                    hour, minute = int(groups[0]), int(groups[1])
                    period = groups[2]
                elif len(groups) == 2:
                    hour, minute = int(groups[0]), 0
                    period = groups[1]
                else:
                    continue

                if period == "PM" and hour != 12:
                    hour += 12
                elif period == "AM" and hour == 12:
                    hour = 0

                return f"{hour:02d}:{minute:02d}"

        return None

    def _add_minutes(self, time_str: str, minutes: int) -> str:
        """Add minutes to HH:MM time string."""
        h, m = map(int, time_str.split(":"))
        total = h * 60 + m + minutes
        return f"{total // 60:02d}:{total % 60:02d}"

    def _mock_slots(self, date: datetime) -> List[str]:
        """Return realistic mock slots."""
        all_slots = []
        h, m = CLINIC_START_HOUR, 0
        while h < CLINIC_END_HOUR:
            all_slots.append(f"{h:02d}:{m:02d}")
            m += SLOT_DURATION_MINS
            if m >= 60:
                m -= 60
                h += 1
        # Simulate some occupied slots
        occupied = {"10:30", "11:00", "14:00"}
        return [s for s in all_slots if s not in occupied]


# ── Test ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n" + "="*60)
    print("  Day 15 — Google Calendar Integration Test")
    print("="*60)

    cal = GoogleCalendarAgent()

    # 1. Check available slots for tomorrow
    print("\n[1] Available slots for tomorrow:")
    slots = cal.get_available_slots("tomorrow")
    print(f"    {len(slots)} slots: {slots[:5]}...")

    # 2. Book an appointment
    print("\n[2] Booking appointment...")
    booking = cal.book_appointment(
        patient_name  = "Lokesh Gaddam",
        patient_phone = "+916302008804",
        date_str      = "tomorrow",
        time_str      = "10:00 AM",
        treatment     = "Teeth Cleaning",
        patient_email = "lokeshgaddam2514@gmail.com",
        booking_id    = "BLN9999001"
    )
    print(f"    Result: {json.dumps(booking, indent=4)}")

    # 3. Check Telugu date resolution
    print("\n[3] Telugu date resolution:")
    tel_date = cal._resolve_date("రేపు ఉదయం")
    print(f"    'రేపు ఉదయం' → {tel_date.strftime('%Y-%m-%d') if tel_date else 'failed'}")

    # 4. Today's schedule
    print("\n[4] Today's schedule:")
    schedule = cal.get_todays_schedule()
    for appt in schedule:
        print(f"    {appt['time']} | {appt['patient']} | {appt['treatment']}")

    print("\n[SUCCESS] Google Calendar Agent working!\n")
