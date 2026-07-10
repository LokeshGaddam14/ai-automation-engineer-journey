"""
Day 14, Part 2 — Postgres Storage Tests
Tests the CallRecord model: save, retrieve, analytics, patient history
"""

import json
import sys
import os
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

from postgres_manager import PostgresManager


def make_call(call_id, phone, name, treatment, language, status="confirmed"):
    """Helper: build a realistic call record dict."""
    return {
        "call_id": call_id,
        "patient_phone": phone,
        "started_at": datetime.utcnow().isoformat(),
        "ended_at":   datetime.utcnow().isoformat(),
        "callStatus": "completed",
        "agentId":    "aria-dental-v2",
        "turns": [
            {"role": "agent",   "content": "Hello! I'm Aria."},
            {"role": "patient", "content": f"I need a {treatment} appointment."},
            {"role": "agent",   "content": "Got it! Booking confirmed."},
        ],
        "extracted_data": {
            "patientName":     name,
            "patientEmail":    f"{name.lower().replace(' ', '.')}@gmail.com",
            "bookingId":       f"BLN{abs(hash(call_id)) % 9000000 + 1000000}",
            "appointmentDate": "2026-07-11",
            "appointmentTime": "10:00 AM",
            "treatment":       treatment,
            "language":        language,
            "booking_status":  status,
            "summary":         f"{name} booked {treatment} for tomorrow 10 AM."
        }
    }


def test_save_single_call():
    """Test 1: Save one call record to Postgres."""
    print("\n" + "="*60)
    print("TEST 1: Save Single Call Record")
    print("="*60)

    pg = PostgresManager()

    call = make_call("call_PG_001", "+916302008804", "Lokesh Gaddam", "Teeth Cleaning", "Telugu")
    call_id = pg.save_call(call)

    print(f"\n   Saved call_id: {call_id}")
    assert call_id == "call_PG_001"

    # Retrieve it back
    record = pg.get_call("call_PG_001")
    print(f"   Retrieved: {record['name']} | {record['treatment']} | {record['booking']}")
    assert record["name"] == "Lokesh Gaddam"
    assert record["treatment"] == "Teeth Cleaning"
    assert record["booking"] == "confirmed"

    print("\n[PASS] TEST 1 PASSED\n")


def test_save_multiple_calls():
    """Test 2: Save multiple calls for analytics."""
    print("="*60)
    print("TEST 2: Save Multiple Calls (Different Languages)")
    print("="*60)

    pg = PostgresManager()

    calls = [
        make_call("call_PG_002", "+919876543210", "Ravi Kumar",   "Root Canal",   "English"),
        make_call("call_PG_003", "+919876543210", "Ravi Kumar",   "Follow-up",    "English"),
        make_call("call_PG_004", "+918765432109", "Priya Sharma", "Cleaning",     "Hindi"),
        make_call("call_PG_005", "+917654321098", "Tamil Patient","Filling",      "Tamil"),
        make_call("call_PG_006", "+916543210987", "No Show",      "Consultation", "English", status="no_booking"),
    ]

    for call in calls:
        pg.save_call(call)
        ext = call["extracted_data"]
        print(f"   Saved: {ext['patientName']} | {ext['language']} | {ext['booking_status']}")

    print(f"\n   Total saved in this batch: {len(calls)}")
    print("\n[PASS] TEST 2 PASSED\n")


def test_patient_history():
    """Test 3: Get a patient's past calls (returning patient context)."""
    print("="*60)
    print("TEST 3: Patient History (Returning Patient)")
    print("="*60)

    pg = PostgresManager()

    # Ravi Kumar has 2 calls from Test 2
    history = pg.get_patient_history("+919876543210", limit=10)

    print(f"\n   History for +919876543210 (Ravi Kumar):")
    print(f"   Total past calls: {len(history)}")
    for h in history:
        print(f"   - {h['date']} | {h['name']} | {h['treatment']} | {h['booking']}")

    assert len(history) >= 2, f"Expected at least 2, got {len(history)}"
    assert history[0]["name"] == "Ravi Kumar"

    # Show how this would be used in Aria's prompt
    print(f"\n   Aria context injection:")
    print(f"   'Welcome back, {history[0]['name']}! I see you've called us {len(history)} time(s).'")

    print("\n[PASS] TEST 3 PASSED\n")


def test_analytics():
    """Test 4: Analytics stats — booking rate, languages, avg duration."""
    print("="*60)
    print("TEST 4: Analytics Dashboard Stats")
    print("="*60)

    pg = PostgresManager()
    stats = pg.get_stats()

    print(f"\n   Analytics snapshot:")
    print(f"   Total calls:        {stats['total_calls']}")
    print(f"   Confirmed bookings: {stats['confirmed_bookings']}")
    print(f"   Booking rate:       {stats['booking_rate_pct']}%")
    print(f"   Avg duration:       {stats['avg_duration_s']}s")
    print(f"   Languages breakdown:")
    for lang, count in stats.get("languages", {}).items():
        print(f"     {lang}: {count} call(s)")

    assert stats["total_calls"] >= 6, "Expected at least 6 total calls from Tests 1+2"
    print("\n[PASS] TEST 4 PASSED\n")


def test_pending_bookings():
    """Test 5: Get confirmed bookings awaiting reminders."""
    print("="*60)
    print("TEST 5: Pending Bookings (for Reminder System)")
    print("="*60)

    pg = PostgresManager()
    bookings = pg.get_pending_bookings()

    print(f"\n   Confirmed bookings found: {len(bookings)}")
    for b in bookings:
        print(f"   - {b['name']} | {b['phone']} | {b['date']} {b['time']} | {b['treatment']}")

    # These are all the calls that should get reminder emails
    confirmed = [b for b in bookings if b["name"] != "No Show"]
    print(f"\n   --> These {len(confirmed)} patients would get WhatsApp reminders!")
    print("\n[PASS] TEST 5 PASSED\n")


def test_upsert_duplicate():
    """Test 6: Saving same call_id twice should not crash (upsert)."""
    print("="*60)
    print("TEST 6: Duplicate Call ID (Upsert Safety)")
    print("="*60)

    pg = PostgresManager()
    call = make_call("call_UPSERT_001", "+910000000000", "Test Patient", "Cleaning", "English")

    pg.save_call(call)
    print("   First save: OK")

    # Update the name and save again with same call_id
    call["extracted_data"]["patientName"] = "Test Patient Updated"
    pg.save_call(call)
    print("   Second save (same ID): OK — no crash!")

    record = pg.get_call("call_UPSERT_001")
    print(f"   Retrieved after upsert: {record['name']}")
    assert record["name"] == "Test Patient Updated"

    print("\n[PASS] TEST 6 PASSED\n")


def test_redis_to_postgres_pipeline():
    """Test 7: Full pipeline — Redis session → Postgres archive."""
    print("="*60)
    print("TEST 7: Redis → Postgres Pipeline (Full Day 14 Flow)")
    print("="*60)

    from redis_manager import RedisSessionManager
    pg = PostgresManager()
    redis = RedisSessionManager()

    call_id = "call_PIPELINE_001"
    phone   = "+916302008804"

    # Step 1: Call starts → Redis
    print("\n   Step 1: Call starts → Redis session created")
    redis.start_session(call_id, phone)

    # Step 2: During call → Redis updated
    print("   Step 2: During call → turns logged to Redis")
    redis.append_turn(call_id, "agent",   "నమస్తే! అపాయింట్మెంట్ కావాలా?")
    redis.append_turn(call_id, "patient", "అవును. రేపు 11 AM కి.")
    redis.update_session(call_id, {
        "state": "booking",
        "extracted_data": {
            "patientName":     "లోకేష్ గడ్డం",
            "patientEmail":    "lokeshgaddam2514@gmail.com",
            "bookingId":       "BLN7654321",
            "appointmentDate": "రేపు",
            "appointmentTime": "11:00 AM",
            "treatment":       "Teeth Cleaning",
            "language":        "Telugu",
            "booking_status":  "confirmed",
            "summary":         "Lokesh booked teeth cleaning for tomorrow 11 AM."
        }
    })

    # Step 3: Call ends → Redis → Postgres
    print("   Step 3: Call ends → Redis finalized → Postgres archive")
    final_session = redis.end_session(call_id)
    pg.save_call(final_session)

    # Step 4: Verify in Postgres
    print("   Step 4: Verify in Postgres...")
    record = pg.get_call(call_id)
    print(f"\n   PIPELINE RESULT:")
    print(f"   Name:     {record['name']}")
    print(f"   Language: {record['language']}")
    print(f"   Booking:  {record['booking']}")
    print(f"   Summary:  {record['summary'][:60]}...")

    assert record["name"] == "లోకేష్ గడ్డం"
    assert record["language"] == "Telugu"
    assert record["booking"] == "confirmed"

    # Redis session is now gone
    gone = redis.get_session(call_id)
    print(f"\n   Redis session after archive: {gone}  (should be None)")
    assert gone is None

    print("\n[PASS] TEST 7 PASSED — Full pipeline working!\n")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Day 14 Part 2 — Postgres Storage Test Suite")
    print("="*60)

    passed = 0
    failed = 0

    tests = [
        test_save_single_call,
        test_save_multiple_calls,
        test_patient_history,
        test_analytics,
        test_pending_bookings,
        test_upsert_duplicate,
        test_redis_to_postgres_pipeline,
    ]

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print(f"  Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("  ALL TESTS PASSED!")
        print("  Redis + Postgres memory layer is fully working!")
    print("="*60 + "\n")
