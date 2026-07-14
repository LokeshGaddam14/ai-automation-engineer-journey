"""
Seed Demo Data for Aria Dashboard
===================================
Inserts realistic demo call records into aria_calls.db so the
admin dashboard shows live data without real Twilio/Bolna calls.

Run from the project root:
    python aria/seed_demo_data.py
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import random
import uuid

# Ensure aria package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from aria.memory.postgres_manager import PostgresManager, CallRecord
from sqlalchemy.orm import Session

TREATMENTS = [
    "Dental Cleaning", "Root Canal", "Cavity Filling", "Teeth Whitening",
    "Crown Fitting", "Extraction", "Orthodontics Consultation", "X-Ray",
    "Gum Treatment", "Implant Consultation",
]

PATIENTS = [
    ("+91-9876543210", "Rahul Sharma"),
    ("+91-8765432109", "Priya Reddy"),
    ("+91-7654321098", "Arjun Nair"),
    ("+91-6543210987", "Sneha Patel"),
    ("+91-9988776655", "Vikram Singh"),
    ("+91-8877665544", "Ananya Iyer"),
    ("+91-7766554433", "Kiran Kumar"),
    ("+91-9123456789", "Divya Menon"),
    ("+91-8234567890", "Suresh Babu"),
    ("+91-7345678901", "Lakshmi Devi"),
]

STATUSES = ["confirmed", "confirmed", "confirmed", "pending", "pending", "cancelled"]
LANGUAGES = ["Telugu", "Telugu", "English", "English", "Hindi"]

SAMPLE_TURNS = [
    [
        {"role": "agent",   "content": "Hello! Welcome to Naveen Advanced Dental Clinic. I'm Aria. How can I help you today?", "timestamp": ""},
        {"role": "patient", "content": "Hi, I'd like to book an appointment for a dental cleaning.", "timestamp": ""},
        {"role": "agent",   "content": "Of course! Could I have your name and preferred date?", "timestamp": ""},
        {"role": "patient", "content": "I'm Rahul. How about this Saturday, 10am?", "timestamp": ""},
        {"role": "agent",   "content": "Perfect! I've booked your appointment for Saturday at 10:00 AM. You'll receive a WhatsApp confirmation shortly.", "timestamp": ""},
    ],
    [
        {"role": "agent",   "content": "నమస్తే! నవీన్ డెంటల్ క్లినిక్కి స్వాగతం. నేను Aria. మీకు ఏమి సహాయపడగలను?", "timestamp": ""},
        {"role": "patient", "content": "నాకు రూట్ కెనాల్ కోసం అపాయింట్మెంట్ కావాలి.", "timestamp": ""},
        {"role": "agent",   "content": "తప్పకుండా! మీ పేరు మరియు ఏ తేదీ కావాలో చెప్పగలరా?", "timestamp": ""},
        {"role": "patient", "content": "నా పేరు ప్రియ. మళ్ళీ నేను రేపు రాగలను.", "timestamp": ""},
        {"role": "agent",   "content": "రేపటి కోసం మీ అపాయింట్మెంట్ నిర్ణయించడమైంది. ధన్యవాద!", "timestamp": ""},
    ],
    [
        {"role": "agent",   "content": "Hello! Welcome to our clinic. How may I assist you?", "timestamp": ""},
        {"role": "patient", "content": "I have a toothache and need to see a doctor urgently.", "timestamp": ""},
        {"role": "agent",   "content": "I understand. We have an emergency slot today at 3 PM. Does that work?", "timestamp": ""},
        {"role": "patient", "content": "Yes, 3 PM works perfectly.", "timestamp": ""},
        {"role": "agent",   "content": "Confirmed! Your emergency appointment is at 3 PM today. See you then!", "timestamp": ""},
    ],
]


def seed():
    pg = PostgresManager()

    with Session(pg.engine) as db:
        existing = db.query(CallRecord).count()
        if existing >= 10:
            print(f"✅ Already have {existing} records — skipping seed (delete aria_calls.db to reset)")
            return

    print("🌱 Seeding demo call records...")

    now = datetime.now(timezone.utc)
    records_added = 0

    for i in range(25):
        phone, name = random.choice(PATIENTS)
        treatment    = random.choice(TREATMENTS)
        status       = random.choice(STATUSES)
        language     = random.choice(LANGUAGES)
        duration     = random.randint(45, 420)
        days_ago     = random.randint(0, 30)
        started_at   = now - timedelta(days=days_ago, hours=random.randint(0, 8), minutes=random.randint(0, 59))
        ended_at     = started_at + timedelta(seconds=duration)

        appt_date = (now + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d")
        appt_time = random.choice(["09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "15:00", "16:00"])

        turns = random.choice(SAMPLE_TURNS).copy()
        base_ts = started_at
        for t in turns:
            t["timestamp"] = base_ts.isoformat()
            base_ts += timedelta(seconds=random.randint(10, 30))

        extracted = {
            "patientName":       name,
            "language":          language,
            "treatment":         treatment,
            "appointmentDate":   appt_date,
            "appointmentTime":   appt_time,
            "booking_status":    status,
            "bookingId":         f"BK-{uuid.uuid4().hex[:8].upper()}",
        }

        record = CallRecord(
            call_id          = f"call-{uuid.uuid4().hex[:16]}",
            patient_phone    = phone,
            started_at       = started_at,
            ended_at         = ended_at,
            duration_secs    = duration,
            language         = language,
            call_status      = "completed",
            patient_name     = name,
            appointment_date = appt_date,
            appointment_time = appt_time,
            treatment        = treatment,
            booking_status   = status,
            extracted_data   = extracted,
            turns            = turns,
            summary          = f"{name} called to book a {treatment} appointment.",
        )

        with Session(pg.engine) as db:
            db.add(record)
            db.commit()
        records_added += 1

    print(f"✅ Seeded {records_added} demo call records into aria_calls.db")
    print("🚀 Now start the backend: cd aria && uvicorn main:app --reload")


if __name__ == "__main__":
    seed()
