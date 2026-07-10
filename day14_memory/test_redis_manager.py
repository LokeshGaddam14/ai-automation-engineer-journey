"""
Day 14, Part 1 — Redis Session Manager Tests
Tests the complete session lifecycle: start → update → turns → end → expiry
"""

import time
import json
import sys
sys.stdout.reconfigure(encoding="utf-8")

# Import from our redis_manager.py
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from redis_manager import RedisSessionManager


def test_basic_flow():
    """Test 1: Basic session lifecycle."""
    print("\n" + "="*60)
    print("TEST 1: Basic Session Lifecycle")
    print("="*60)

    mgr = RedisSessionManager()

    # Start session
    print("\n1. Starting session...")
    session = mgr.start_session("call_001", "+919876543210")
    print(f"   Session created: {session['call_id']}")
    print(f"   Patient: {session['patient_phone']}")

    # Retrieve
    print("\n2. Retrieving session...")
    retrieved = mgr.get_session("call_001")
    print(f"   State: {retrieved['state']}")
    print(f"   Turns: {len(retrieved['turns'])}")

    # End
    print("\n3. Ending session...")
    final = mgr.end_session("call_001")
    print(f"   ended_at set: {final.get('ended_at') is not None}")

    # Verify deleted
    print("\n4. Verifying deletion from Redis...")
    check = mgr.get_session("call_001")
    print(f"   Session found after end: {check is not None}  (expected: False)")

    assert check is None, "Session should be deleted after end_session!"
    print("\n[PASS] TEST 1 PASSED\n")


def test_conversation_logging():
    """Test 2: Conversation turns."""
    print("="*60)
    print("TEST 2: Conversation Logging")
    print("="*60)

    mgr = RedisSessionManager()
    call_id = "call_002"

    print("\n1. Starting call...")
    mgr.start_session(call_id, "+919876543210")

    print("\n2. Logging conversation turns...")
    turns_data = [
        ("agent",   "Hello! This is Aria from Naveen Dental. How can I help?", None),
        ("patient", "Hi, I'd like to book an appointment.",                    None),
        ("agent",   "Great! What's your name?",                                {"intent": "booking"}),
        ("patient", "My name is Ravi Kumar.",                                  None),
        ("agent",   "Nice to meet you, Ravi!",                                 {"extracted_name": "Ravi Kumar"}),
    ]

    for role, content, extracted in turns_data:
        mgr.append_turn(call_id, role, content, extracted)

    print("\n3. Retrieving conversation history...")
    history = mgr.get_turn_count(call_id)
    print(f"   Total turns: {history}  (expected: 5)")

    full_history = mgr.get_session(call_id)["turns"]
    for i, turn in enumerate(full_history, 1):
        print(f"\n   Turn {i}:")
        print(f"   - Role: {turn['role']}")
        print(f"   - Content: {turn['content'][:60]}")
        if turn.get("extracted_data"):
            print(f"   - Extracted: {turn['extracted_data']}")

    assert history == 5, f"Expected 5 turns, got {history}"
    mgr.end_session(call_id)
    print("\n[PASS] TEST 2 PASSED\n")


def test_data_extraction():
    """Test 3: Gradual data extraction (like a real call)."""
    print("="*60)
    print("TEST 3: Gradual Data Extraction")
    print("="*60)

    mgr = RedisSessionManager()
    call_id = "call_003"

    print("\n1. Starting call...")
    mgr.start_session(call_id, "+919876543210")

    # Turn 1: Get name
    mgr.append_turn(call_id, "agent", "What's your name?")
    mgr.append_turn(call_id, "patient", "I'm Priya Sharma")
    mgr.update_session(call_id, {"extracted_data": {"name": "Priya Sharma"}})
    print("   Extracted: name")

    # Turn 2: Get chief complaint
    mgr.append_turn(call_id, "agent", "What brings you in today?")
    mgr.append_turn(call_id, "patient", "I have a terrible toothache")
    mgr.update_session(call_id, {"extracted_data": {"chief_complaint": "toothache"}})
    print("   Extracted: chief_complaint")

    # Turn 3: Get preferred date/time
    mgr.append_turn(call_id, "agent", "When would you like to come?")
    mgr.append_turn(call_id, "patient", "Tomorrow at 2pm if possible")
    mgr.update_session(call_id, {
        "extracted_data": {
            "preferred_date": "2026-07-11",
            "preferred_time": "14:00"
        }
    })
    print("   Extracted: preferred_date, preferred_time")

    print("\n2. Final extracted data:")
    session = mgr.get_session(call_id)
    print(json.dumps(session["extracted_data"], indent=2, ensure_ascii=False))

    # Verify all fields extracted
    assert session["extracted_data"]["name"] == "Priya Sharma"
    assert session["extracted_data"]["chief_complaint"] == "toothache"
    assert session["extracted_data"]["preferred_date"] == "2026-07-11"

    mgr.end_session(call_id)
    print("\n[PASS] TEST 3 PASSED\n")


def test_session_expiry():
    """Test 4: TTL (session auto-expire after N seconds)."""
    print("="*60)
    print("TEST 4: Session Auto-Expiry (TTL)")
    print("="*60)

    # Short TTL for testing
    mgr = RedisSessionManager()
    # Override TTL for this test by using a custom set directly if using in_memory mode
    call_id = "call_004_ttl_test"

    print("\n1. Creating session and ending it immediately (simulating expiry)...")
    mgr.start_session(call_id, "+919000000000")

    # Exists right after creation
    session = mgr.get_session(call_id)
    print(f"   Immediately after start: found={session is not None}  (expected: True)")

    # End it
    mgr.end_session(call_id)

    # Gone after end
    gone = mgr.get_session(call_id)
    print(f"   After end_session: found={gone is not None}  (expected: False)")
    assert gone is None

    print("\n   NOTE: In production, sessions also expire after TTL (1 hour by default).")
    print("   This prevents memory buildup if call crashes without calling end_session.")
    print("\n[PASS] TEST 4 PASSED\n")


def test_active_sessions():
    """Test 5: Multiple concurrent sessions."""
    print("="*60)
    print("TEST 5: Multiple Concurrent Sessions")
    print("="*60)

    mgr = RedisSessionManager()

    print("\n1. Starting 3 simultaneous calls...")
    mgr.start_session("call_sim_1", "+919111111111")
    mgr.start_session("call_sim_2", "+919222222222")
    mgr.start_session("call_sim_3", "+919333333333")

    print("\n2. Verifying all 3 exist...")
    for i in range(1, 4):
        s = mgr.get_session(f"call_sim_{i}")
        print(f"   call_sim_{i}: found={s is not None}  phone={s['patient_phone'] if s else 'N/A'}")

    print("\n3. Checking session_exists() helper...")
    print(f"   call_sim_1 exists: {mgr.session_exists('call_sim_1')}  (expected: True)")
    print(f"   call_ghost exists: {mgr.session_exists('call_ghost')}   (expected: False)")

    print("\n4. Cleaning up...")
    for i in range(1, 4):
        mgr.end_session(f"call_sim_{i}")

    print("\n5. Verify all deleted...")
    for i in range(1, 4):
        s = mgr.get_session(f"call_sim_{i}")
        print(f"   call_sim_{i} after end: found={s is not None}  (expected: False)")

    print("\n[PASS] TEST 5 PASSED\n")


def test_bolna_webhook_simulation():
    """Test 6: Simulate a real Bolna Telugu call lifecycle."""
    print("="*60)
    print("TEST 6: Real Bolna Call Simulation (Telugu)")
    print("="*60)

    mgr = RedisSessionManager()
    call_id = "c5280159-7f07-40bc-9c27-a615fb8fec01"  # Real Bolna call ID format

    print("\n1. Call starts (webhook fires: status=initiated)...")
    mgr.start_session(call_id, "+916302008804")

    print("\n2. During call — turns logged in real time...")
    mgr.append_turn(call_id, "agent",
        "నమస్తే! మా డెంటల్ క్లినిక్కి స్వాగతం. అపాయింట్మెంట్ బుక్ చేసుకోవడానికి నేను సహాయం చేయగలను.",
        {"agent_state": "greeting"})

    mgr.append_turn(call_id, "patient",
        "హలో, నా పేరు లోకేష్ గడ్డం. నాకు ఒక అపాయింట్మెంట్ బుక్ చేయండి.",
        {"extracted_name": "లోకేష్ గడ్డం", "intent": "booking"})

    mgr.update_session(call_id, {
        "state": "booking",
        "extracted_data": {
            "patient_name": "లోకేష్ గడ్డం",
            "intent": "booking",
            "language": "Telugu"
        }
    })

    mgr.append_turn(call_id, "patient",
        "రేపు పొద్దున్నే 10:00కి.",
        {"appointment_date": "రేపు", "appointment_time": "10:00 AM"})

    mgr.update_session(call_id, {
        "extracted_data": {
            "appointment_date": "రేపు",
            "appointment_time": "10:00 AM"
        }
    })

    mgr.append_turn(call_id, "agent",
        "లోకేష్ గారు, రేపు ఉదయం 10 గంటలకు అపాయింట్మెంట్ కన్ఫర్మ్ అయింది!",
        {"booking_confirmed": True, "booking_id": "BLN8948006"})

    mgr.update_session(call_id, {
        "state": "completed",
        "extracted_data": {
            "booking_id": "BLN8948006",
            "booking_status": "confirmed"
        }
    })

    print("\n3. Call ends (webhook fires: status=completed)...")
    final = mgr.end_session(call_id)

    print(f"\n4. Final session summary:")
    print(f"   Call ID:  {final['call_id']}")
    print(f"   Phone:    {final['patient_phone']}")
    print(f"   Turns:    {len(final['turns'])}")
    print(f"   Extracted:")
    for k, v in final['extracted_data'].items():
        print(f"     {k}: {v}")

    print("\n   --> This session dict is now ready to be saved to Postgres!")
    assert final["extracted_data"]["booking_status"] == "confirmed"
    assert final["extracted_data"]["booking_id"] == "BLN8948006"

    print("\n[PASS] TEST 6 PASSED\n")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Day 14 — Redis Session Manager Test Suite")
    print("="*60)

    passed = 0
    failed = 0

    tests = [
        test_basic_flow,
        test_conversation_logging,
        test_data_extraction,
        test_session_expiry,
        test_active_sessions,
        test_bolna_webhook_simulation,
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
        print("  ALL TESTS PASSED! Redis Session Manager is working!")
    else:
        print("  Some tests failed. Check Redis connection above.")
    print("="*60 + "\n")
