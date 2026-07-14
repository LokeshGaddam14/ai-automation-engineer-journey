"""
Aria — Complete Test Suite
===========================
20+ tests covering all core modules.

Run:
    cd ai-automation
    pytest aria/tests/test_aria.py -v
    pytest aria/tests/test_aria.py -v --tb=short   # Brief tracebacks
"""

import json
import pytest
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def redis_mgr():
    """RedisSessionManager in pure in-memory mode (no external connections)."""
    from aria.memory.redis_manager import RedisSessionManager
    mgr = RedisSessionManager.__new__(RedisSessionManager)
    mgr.mode = "in_memory"
    mgr._memory = {}
    mgr.client = None
    return mgr


@pytest.fixture
def postgres_mgr(tmp_path):
    """PostgresManager with a fresh SQLite database (zero config)."""
    from aria.memory.postgres_manager import PostgresManager
    db_path = f"sqlite:///{tmp_path}/test_aria.db"
    return PostgresManager(db_url=db_path)


@pytest.fixture
def sample_session():
    """A realistic completed call session dict."""
    return {
        "call_id":       "call_TEST_001",
        "patient_phone": "+916302008804",
        "started_at":    datetime.now(timezone.utc).isoformat(),
        "ended_at":      datetime.now(timezone.utc).isoformat(),
        "callStatus":    "completed",
        "agentId":       "aria-dental-v1",
        "turns": [
            {"role": "agent",   "content": "Hello! Welcome to Naveen Dental Clinic."},
            {"role": "patient", "content": "I need an appointment."},
            {"role": "agent",   "content": "Sure! What date works for you?"},
            {"role": "patient", "content": "Tomorrow at 10 AM."},
            {"role": "agent",   "content": "Confirmed! Booking ID: BLN9999001"},
        ],
        "extracted_data": {
            "patientName":    "Lokesh Gaddam",
            "patientEmail":   "lokeshgaddam2514@gmail.com",
            "bookingId":      "BLN9999001",
            "appointmentDate": "tomorrow",
            "appointmentTime": "10:00 AM",
            "treatment":      "Teeth Cleaning",
            "booking_status": "confirmed",
            "language":       "English",
            "summary":        "Patient booked teeth cleaning for tomorrow 10 AM.",
        }
    }


@pytest.fixture
def sample_call_state():
    """A fully populated CallState for LangGraph tests."""
    return {
        "call_id":          "call_LG_001",
        "patient_phone":    "+916302008804",
        "language":         "English",
        "started_at":       datetime.now().isoformat(),
        "messages":         [
            {"role": "patient", "content": "I need an appointment", "timestamp": datetime.now().isoformat()}
        ],
        "turn_count":       1,
        "patient_name":     "Lokesh Gaddam",
        "appointment_date": "tomorrow",
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


# ═══════════════════════════════════════════════════════════════════════════════
# REDIS SESSION MANAGER TESTS (Day 14)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRedisSessionManager:

    def test_redis_session_start(self, redis_mgr):
        """Session is created with correct initial values."""
        session = redis_mgr.start_session("call_001", "+916302008804")
        assert session["call_id"] == "call_001"
        assert session["patient_phone"] == "+916302008804"
        assert session["state"] == "greeting"
        assert session["turns"] == []
        assert session["extracted_data"] == {}
        assert session["ended_at"] is None

    def test_redis_session_get(self, redis_mgr):
        """Session can be retrieved after creation."""
        redis_mgr.start_session("call_002", "+91111111111")
        session = redis_mgr.get_session("call_002")
        assert session is not None
        assert session["call_id"] == "call_002"

    def test_redis_session_get_nonexistent(self, redis_mgr):
        """Returns None for non-existent sessions."""
        result = redis_mgr.get_session("nonexistent_call")
        assert result is None

    def test_redis_append_turn(self, redis_mgr):
        """Turns are appended in order with correct role."""
        redis_mgr.start_session("call_003", "+91222222222")
        redis_mgr.append_turn("call_003", "agent",   "Hello!")
        redis_mgr.append_turn("call_003", "patient", "I need an appointment.")
        redis_mgr.append_turn("call_003", "agent",   "Sure! What date?")

        session = redis_mgr.get_session("call_003")
        assert len(session["turns"]) == 3
        assert session["turns"][0]["role"] == "agent"
        assert session["turns"][1]["role"] == "patient"
        assert session["turns"][2]["content"] == "Sure! What date?"

    def test_redis_append_turn_with_extracted_data(self, redis_mgr):
        """Extracted data is stored alongside the turn."""
        redis_mgr.start_session("call_004", "+91333333333")
        redis_mgr.append_turn(
            "call_004", "patient", "Book for tomorrow",
            extracted_data={"intent": "booking", "date": "tomorrow"}
        )
        session = redis_mgr.get_session("call_004")
        assert session["turns"][0]["extracted_data"]["intent"] == "booking"

    def test_redis_update_session(self, redis_mgr):
        """Session state is updated correctly."""
        redis_mgr.start_session("call_005", "+91444444444")
        redis_mgr.update_session("call_005", {
            "state": "booking",
            "extracted_data": {"name": "Ravi Kumar", "treatment": "Cleaning"}
        })
        session = redis_mgr.get_session("call_005")
        assert session["state"] == "booking"
        assert session["extracted_data"]["name"] == "Ravi Kumar"

    def test_redis_end_session(self, redis_mgr):
        """Session is removed from Redis and returned with ended_at set."""
        redis_mgr.start_session("call_006", "+91555555555")
        final = redis_mgr.end_session("call_006")
        assert final is not None
        assert final["ended_at"] is not None
        # Session should be gone
        assert redis_mgr.get_session("call_006") is None

    def test_redis_end_nonexistent_session(self, redis_mgr):
        """Ending non-existent session returns None gracefully."""
        result = redis_mgr.end_session("ghost_call")
        assert result is None

    def test_redis_session_exists(self, redis_mgr):
        """session_exists() returns correct boolean."""
        redis_mgr.start_session("call_007", "+91666666666")
        assert redis_mgr.session_exists("call_007") is True
        assert redis_mgr.session_exists("missing") is False

    def test_redis_get_turn_count(self, redis_mgr):
        """Turn count is accurate."""
        redis_mgr.start_session("call_008", "+91777777777")
        assert redis_mgr.get_turn_count("call_008") == 0
        redis_mgr.append_turn("call_008", "agent", "Hi")
        redis_mgr.append_turn("call_008", "patient", "Hello")
        assert redis_mgr.get_turn_count("call_008") == 2


# ═══════════════════════════════════════════════════════════════════════════════
# POSTGRES MANAGER TESTS (Day 14)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPostgresManager:

    def test_postgres_save_call(self, postgres_mgr, sample_session):
        """Call record is saved and retrievable."""
        call_id = postgres_mgr.save_call(sample_session)
        assert call_id == "call_TEST_001"

        record = postgres_mgr.get_call("call_TEST_001")
        assert record is not None
        assert record["call_id"] == "call_TEST_001"
        assert record["name"] == "Lokesh Gaddam"

    def test_postgres_get_patient_history(self, postgres_mgr, sample_session):
        """Patient history returns sorted records."""
        postgres_mgr.save_call(sample_session)

        history = postgres_mgr.get_patient_history("+916302008804")
        assert len(history) == 1
        assert history[0]["name"] == "Lokesh Gaddam"
        assert history[0]["treatment"] == "Teeth Cleaning"
        assert history[0]["booking"] == "confirmed"

    def test_postgres_upsert_duplicate(self, postgres_mgr, sample_session):
        """Duplicate saves don't raise errors (upsert behavior)."""
        postgres_mgr.save_call(sample_session)
        postgres_mgr.save_call(sample_session)  # Should not error

        history = postgres_mgr.get_patient_history("+916302008804")
        assert len(history) == 1  # Still just one record

    def test_postgres_get_stats(self, postgres_mgr, sample_session):
        """Stats returns correct aggregate values."""
        postgres_mgr.save_call(sample_session)
        stats = postgres_mgr.get_stats()

        assert stats["total_calls"] >= 1
        assert stats["confirmed_bookings"] >= 1
        assert stats["booking_rate_pct"] > 0

    def test_postgres_get_pending_bookings(self, postgres_mgr, sample_session):
        """Pending bookings returns confirmed appointments."""
        postgres_mgr.save_call(sample_session)
        bookings = postgres_mgr.get_pending_bookings()
        assert len(bookings) >= 1
        assert bookings[0]["phone"] == "+916302008804"

    def test_postgres_search_calls(self, postgres_mgr, sample_session):
        """Search returns matching records."""
        postgres_mgr.save_call(sample_session)
        results = postgres_mgr.search_calls("Lokesh")
        assert len(results) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# GOOGLE CALENDAR TESTS (Day 15)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoogleCalendarAgent:

    @pytest.fixture
    def cal(self):
        """GoogleCalendarAgent in mock mode."""
        from aria.integrations.google_calendar import GoogleCalendarAgent
        agent = GoogleCalendarAgent.__new__(GoogleCalendarAgent)
        agent.service = None
        agent._mock_mode = True
        return agent

    def test_calendar_get_available_slots(self, cal):
        """Returns list of time slots."""
        slots = cal.get_available_slots("tomorrow")
        assert isinstance(slots, list)
        assert len(slots) > 0
        assert "09:00" in slots

    def test_calendar_get_slots_excludes_occupied(self, cal):
        """Mock slots exclude hardcoded occupied times."""
        slots = cal.get_available_slots("tomorrow")
        assert "10:30" not in slots  # Mock occupied
        assert "14:00" not in slots  # Mock occupied

    def test_calendar_book_appointment(self, cal):
        """Mock booking returns confirmed status."""
        result = cal.book_appointment(
            patient_name  = "Lokesh Gaddam",
            patient_phone = "+916302008804",
            date_str      = "tomorrow",
            time_str      = "10:00 AM",
            treatment     = "Teeth Cleaning",
            booking_id    = "BLN9999001"
        )
        assert result["status"] == "confirmed"
        assert "event_id" in result
        assert result["mock"] is True

    def test_calendar_cancel_appointment(self, cal):
        """Mock cancel returns cancelled status."""
        result = cal.cancel_appointment("mock_event_123")
        assert result["status"] == "cancelled"

    def test_calendar_resolve_date_tomorrow(self, cal):
        """'tomorrow' resolves to tomorrow's date."""
        from datetime import datetime, timezone, timedelta
        result = cal._resolve_date("tomorrow")
        expected = datetime.now() + timedelta(days=1)
        assert result.date() == expected.date()

    def test_calendar_resolve_date_telugu(self, cal):
        """Telugu 'రేపు' resolves to tomorrow."""
        from datetime import datetime, timezone, timedelta
        result = cal._resolve_date("రేపు")
        expected = datetime.now() + timedelta(days=1)
        assert result.date() == expected.date()

    def test_calendar_normalize_time_12hr(self, cal):
        """'10:00 AM' normalizes to '10:00'."""
        assert cal._normalize_time("10:00 AM") == "10:00"

    def test_calendar_normalize_time_pm(self, cal):
        """'2:30 PM' normalizes to '14:30'."""
        assert cal._normalize_time("2:30 PM") == "14:30"

    def test_calendar_normalize_time_24hr(self, cal):
        """'14:30' passes through unchanged."""
        assert cal._normalize_time("14:30") == "14:30"


# ═══════════════════════════════════════════════════════════════════════════════
# TWILIO NOTIFIER TESTS (Day 15)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTwilioNotifier:

    @pytest.fixture
    def notifier(self):
        """TwilioNotifier in mock mode."""
        from aria.integrations.twilio_client import TwilioNotifier
        n = TwilioNotifier.__new__(TwilioNotifier)
        n.client = None
        n._mock_mode = True
        return n

    def test_twilio_send_sms(self, notifier):
        """SMS returns sent status in mock mode."""
        result = notifier.send_sms("+916302008804", "Test SMS message")
        assert result["status"] == "sent"
        assert result["mock"] is True
        assert result["channel"] == "sms"

    def test_twilio_send_whatsapp(self, notifier):
        """WhatsApp returns sent status in mock mode."""
        result = notifier.send_whatsapp("+916302008804", "Test WhatsApp")
        assert result["status"] == "sent"
        assert result["channel"] == "whatsapp"

    def test_twilio_booking_confirmation(self, notifier):
        """Booking confirmation sends via correct channel."""
        result = notifier.send_booking_confirmation(
            phone        = "+916302008804",
            patient_name = "Lokesh Gaddam",
            date         = "2026-07-15",
            time         = "10:00",
            treatment    = "Teeth Cleaning",
            booking_id   = "BLN9999001",
            channel      = "whatsapp"
        )
        assert result["status"] == "sent"

    def test_twilio_reminder(self, notifier):
        """Reminder message is sent."""
        result = notifier.send_reminder(
            phone        = "+916302008804",
            patient_name = "Ravi Kumar",
            date         = "2026-07-15",
            time         = "14:00",
            channel      = "sms"
        )
        assert result["status"] == "sent"

    def test_twilio_cancellation(self, notifier):
        """Cancellation notice is sent."""
        result = notifier.send_cancellation(
            phone        = "+916302008804",
            patient_name = "Priya Sharma",
            date         = "2026-07-15",
            time         = "11:00",
        )
        assert result["status"] == "sent"


# ═══════════════════════════════════════════════════════════════════════════════
# LANGGRAPH ORCHESTRATOR TESTS (Day 15)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLangGraphOrchestrator:

    def test_orchestrator_greeting_english(self, sample_call_state):
        """Greeting agent returns English welcome message."""
        from aria.agents.orchestrator import greeting_agent
        sample_call_state["language"] = "English"
        result = greeting_agent(sample_call_state)
        assert "Aria" in result["last_response"]
        assert result["current_agent"] == "greeting"

    def test_orchestrator_greeting_telugu(self, sample_call_state):
        """Greeting agent returns Telugu message for Telugu language."""
        from aria.agents.orchestrator import greeting_agent
        sample_call_state["language"] = "Telugu"
        result = greeting_agent(sample_call_state)
        assert "Aria" in result["last_response"]
        assert "నమస్తే" in result["last_response"]

    def test_orchestrator_booking_flow(self, sample_call_state):
        """Booking agent confirms when all info is provided."""
        from aria.agents.orchestrator import booking_agent
        # All required fields pre-filled in sample_call_state
        result = booking_agent(sample_call_state)
        assert result["booking_confirmed"] is True
        assert result["booking_id"] is not None
        assert result["booking_id"].startswith("BLN")

    def test_orchestrator_booking_asks_name(self, sample_call_state):
        """Booking agent asks for name if missing."""
        from aria.agents.orchestrator import booking_agent
        sample_call_state["patient_name"] = None
        result = booking_agent(sample_call_state)
        assert result["booking_confirmed"] is False
        assert "name" in result["last_response"].lower() or "పేరు" in result["last_response"]

    def test_orchestrator_info_agent(self, sample_call_state):
        """Info agent returns pricing info."""
        from aria.agents.orchestrator import info_agent
        result = info_agent(sample_call_state)
        assert "₹" in result["last_response"]
        assert result["next_agent"] == "booking"

    def test_orchestrator_emergency_agent(self, sample_call_state):
        """Emergency agent sets urgency level."""
        from aria.agents.orchestrator import emergency_agent
        result = emergency_agent(sample_call_state)
        assert result["urgency_level"] == "emergency"
        assert result["next_agent"] == "booking"

    def test_orchestrator_escalation_agent(self, sample_call_state):
        """Escalation agent ends the conversation."""
        from aria.agents.orchestrator import escalation_agent
        result = escalation_agent(sample_call_state)
        assert result["is_complete"] is True
        assert result["escalation_reason"] is not None

    def test_orchestrator_intent_detection_booking(self, sample_call_state):
        """Greeting agent detects booking intent."""
        from aria.agents.orchestrator import greeting_agent
        sample_call_state["messages"] = [
            {"role": "patient", "content": "I need to book an appointment", "timestamp": "2026-07-11T00:00:00"}
        ]
        result = greeting_agent(sample_call_state)
        assert result["intent"] == "booking"

    def test_orchestrator_intent_detection_emergency(self, sample_call_state):
        """Greeting agent detects emergency intent from pain keywords."""
        from aria.agents.orchestrator import greeting_agent
        sample_call_state["messages"] = [
            {"role": "patient", "content": "I have severe tooth pain", "timestamp": "2026-07-11T00:00:00"}
        ]
        result = greeting_agent(sample_call_state)
        assert result["intent"] == "emergency"


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED CALL HANDLER TESTS (Day 14)
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnifiedCallHandler:

    @pytest.fixture
    def handler(self, tmp_path):
        """UnifiedCallHandler with in-memory Redis and SQLite Postgres."""
        from aria.agents.call_handler import UnifiedCallHandler
        from aria.memory.redis_manager import RedisSessionManager
        from aria.memory.postgres_manager import PostgresManager

        h = UnifiedCallHandler.__new__(UnifiedCallHandler)

        # In-memory Redis
        redis = RedisSessionManager.__new__(RedisSessionManager)
        redis.mode = "in_memory"
        redis._memory = {}
        redis.client = None
        h.redis = redis

        # SQLite Postgres
        db_path = f"sqlite:///{tmp_path}/handler_test.db"
        h.postgres = PostgresManager(db_url=db_path)

        return h

    def test_handle_incoming_call(self, handler):
        """start_call creates a Redis session."""
        session = handler.start_call("call_H001", "+916302008804")
        assert session["call_id"] == "call_H001"
        assert session["patient_phone"] == "+916302008804"
        assert session["is_returning_patient"] is False

    def test_handle_returning_patient(self, handler, sample_session):
        """Returning patient flag is set correctly."""
        # Archive a past call
        handler.postgres.save_call(sample_session)
        # New call from same phone
        session = handler.start_call("call_H002", "+916302008804")
        assert session["is_returning_patient"] is True
        assert session["previous_calls"] == 1

    def test_finalize_call(self, handler, sample_session):
        """end_call archives to Postgres and returns summary."""
        handler.redis.start_session("call_TEST_001", "+916302008804")
        summary = handler.end_call("call_TEST_001", sample_session)
        assert summary.get("archived") is True
        assert summary.get("call_id") == "call_TEST_001"

    def test_full_call_flow(self, handler):
        """Complete call lifecycle: start → end → archive."""
        call_id = "call_FULL_001"
        phone   = "+919876543210"

        # 1. Start
        session = handler.start_call(call_id, phone)
        assert session is not None

        # 2. End
        bolna_payload = {
            "executionId":    call_id,
            "patientPhone":   phone,
            "patientName":    "Test Patient",
            "appointmentDate": "2026-07-15",
            "appointmentTime": "11:00 AM",
            "treatment":      "Checkup",
            "hasBooking":     True,
            "language":       "English",
        }
        summary = handler.end_call(call_id, bolna_payload)
        assert summary["archived"] is True

        # 3. Verify in Postgres
        history = handler.postgres.get_patient_history(phone)
        assert len(history) >= 1
