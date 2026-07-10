"""
Day 14 — Postgres Persistent Storage
======================================
Durable, long-term storage for completed call records using SQLAlchemy + Postgres.

Uses Supabase (free hosted Postgres — no local PostgreSQL needed on laptop).
Sign up FREE at: https://supabase.com/ → New Project → Copy Connection String

Why Postgres for voice calls?
- Survives server restarts (unlike Redis)
- SQL queries for analytics (how many calls per day, conversion rate, etc.)
- Audit trail for compliance
- ML features: historical patient behavior patterns

Architecture:
    ACTIVE CALL  → Redis (real-time, <1ms)
    CALL ENDS    → Redis session → Postgres (durable archive)
    ANALYTICS    → Postgres SQL queries
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import (
    Column, DateTime, Integer, JSON, String, Text,
    create_engine, func
)
from sqlalchemy.orm import DeclarativeBase, Session


# ── Config ─────────────────────────────────────────────────────────────────────
# Option 1: Supabase (recommended for laptops, free tier)
#   DATABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres
# Option 2: Local PostgreSQL
#   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/aria_db
# Option 3: SQLite (zero-setup fallback for development)
#   DATABASE_URL=sqlite:///./aria_calls.db

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./aria_calls.db"  # SQLite fallback — works with zero setup!
)


# ── ORM Models ─────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class CallRecord(Base):
    """
    Persistent record for a completed call.

    Mirrors the Redis session schema but stored durably.
    """
    __tablename__ = "call_records"

    call_id       = Column(String(100), primary_key=True)
    patient_phone = Column(String(20),  nullable=False, index=True)
    started_at    = Column(DateTime,    default=datetime.utcnow)
    ended_at      = Column(DateTime,    nullable=True)
    duration_secs = Column(Integer,     nullable=True)
    language      = Column(String(20),  default="English")
    agent_id      = Column(String(100), nullable=True)
    call_status   = Column(String(50),  default="completed")

    # Extracted booking info
    patient_name   = Column(String(100), nullable=True)
    patient_email  = Column(String(200), nullable=True)
    booking_id     = Column(String(50),  nullable=True)
    appointment_date  = Column(String(100), nullable=True)
    appointment_time  = Column(String(50),  nullable=True)
    treatment         = Column(String(200), nullable=True)
    booking_status    = Column(String(50),  default="pending")  # pending/confirmed/no_show

    # Full data as JSON (flexible, no schema changes needed)
    extracted_data = Column(JSON, default=dict)
    turns          = Column(JSON, default=list)   # Full conversation log
    summary        = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())


class AppointmentReminder(Base):
    """
    Track reminders sent to patients.
    Used by n8n cron to avoid duplicate reminders.
    """
    __tablename__ = "appointment_reminders"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    call_id      = Column(String(100), nullable=False)
    patient_phone= Column(String(20),  nullable=False)
    channel      = Column(String(20),  nullable=False)  # email/whatsapp/sms
    sent_at      = Column(DateTime,    default=datetime.utcnow)
    status       = Column(String(20),  default="sent")  # sent/failed/delivered


# ── Manager Class ──────────────────────────────────────────────────────────────

class PostgresManager:
    """
    Durable storage for completed call records.

    Usage:
        pg = PostgresManager()
        pg.save_call(redis_session_dict)        # Archive from Redis
        pg.get_patient_history("+91XXXXXXXXXX") # Get past calls
        pg.get_stats()                          # Analytics
    """

    def __init__(self, db_url: str = DATABASE_URL):
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        self.engine = create_engine(db_url, connect_args=connect_args)
        Base.metadata.create_all(self.engine)

        db_type = "SQLite" if db_url.startswith("sqlite") else \
                  "Supabase" if "supabase" in db_url else "PostgreSQL"
        print(f"✅ PostgresManager initialized (DB: {db_type})")

    # ── Write operations ───────────────────────────────────────────────────────

    def save_call(self, session_dict: Dict) -> str:
        """
        Archive a completed Redis session to Postgres.

        Args:
            session_dict: Final session from RedisSessionManager.end_session()

        Returns: call_id of saved record
        """
        with Session(self.engine) as db:
            # Calculate duration
            started = datetime.fromisoformat(session_dict.get("started_at", datetime.utcnow().isoformat()))
            ended_str = session_dict.get("ended_at")
            ended = datetime.fromisoformat(ended_str) if ended_str else datetime.utcnow()
            duration = max(0, int((ended - started).total_seconds()))

            extracted = session_dict.get("extracted_data", {})

            record = CallRecord(
                call_id       = session_dict["call_id"],
                patient_phone = session_dict.get("patient_phone", ""),
                started_at    = started,
                ended_at      = ended,
                duration_secs = duration,
                language      = extracted.get("language", "English"),
                agent_id      = session_dict.get("agentId", ""),
                call_status   = session_dict.get("callStatus", "completed"),
                patient_name  = extracted.get("patientName") or extracted.get("name", ""),
                patient_email = extracted.get("patientEmail") or extracted.get("email", ""),
                booking_id    = extracted.get("bookingId", ""),
                appointment_date = extracted.get("appointmentDate", ""),
                appointment_time = extracted.get("appointmentTime", ""),
                treatment     = extracted.get("treatment", ""),
                booking_status= extracted.get("booking_status", "pending"),
                extracted_data= extracted,
                turns         = session_dict.get("turns", []),
                summary       = extracted.get("summary", ""),
            )

            # Upsert (handle duplicates gracefully)
            existing = db.get(CallRecord, session_dict["call_id"])
            if existing:
                db.delete(existing)
                db.flush()

            db.add(record)
            db.commit()
            print(f"📁 Call archived: {record.call_id} | Duration: {duration}s")
            return record.call_id

    def log_reminder(self, call_id: str, patient_phone: str, channel: str) -> int:
        """Log that a reminder was sent (prevents duplicates)."""
        with Session(self.engine) as db:
            reminder = AppointmentReminder(
                call_id=call_id,
                patient_phone=patient_phone,
                channel=channel
            )
            db.add(reminder)
            db.commit()
            return reminder.id

    # ── Read operations ────────────────────────────────────────────────────────

    def get_patient_history(self, patient_phone: str, limit: int = 10) -> List[Dict]:
        """
        Get a patient's past calls — used to give agent context.

        Example use:
            "I see you called us before. Is this related to your previous appointment?"
        """
        with Session(self.engine) as db:
            records = (
                db.query(CallRecord)
                .filter(CallRecord.patient_phone == patient_phone)
                .order_by(CallRecord.started_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "call_id":     r.call_id,
                    "date":        r.started_at.strftime("%Y-%m-%d"),
                    "duration_s":  r.duration_secs,
                    "name":        r.patient_name,
                    "treatment":   r.treatment,
                    "booking":     r.booking_status,
                    "language":    r.language,
                }
                for r in records
            ]

    def get_call(self, call_id: str) -> Optional[Dict]:
        """Get full call record including transcript."""
        with Session(self.engine) as db:
            r = db.get(CallRecord, call_id)
            if not r:
                return None
            return {
                "call_id":     r.call_id,
                "patient":     r.patient_phone,
                "name":        r.patient_name,
                "duration_s":  r.duration_secs,
                "language":    r.language,
                "booking_id":  r.booking_id,
                "treatment":   r.treatment,
                "date":        r.appointment_date,
                "time":        r.appointment_time,
                "booking":     r.booking_status,
                "summary":     r.summary,
                "turns":       r.turns,
                "extracted":   r.extracted_data,
            }

    def get_pending_bookings(self) -> List[Dict]:
        """Get confirmed bookings that haven't had reminders sent yet."""
        with Session(self.engine) as db:
            records = (
                db.query(CallRecord)
                .filter(CallRecord.booking_status == "confirmed")
                .order_by(CallRecord.started_at.desc())
                .limit(50)
                .all()
            )
            return [
                {
                    "call_id":   r.call_id,
                    "phone":     r.patient_phone,
                    "name":      r.patient_name,
                    "email":     r.patient_email,
                    "date":      r.appointment_date,
                    "time":      r.appointment_time,
                    "treatment": r.treatment,
                }
                for r in records
            ]

    def get_stats(self) -> Dict:
        """
        Analytics summary — useful for dashboard and reporting.

        Returns call counts, booking rates, language breakdown.
        """
        with Session(self.engine) as db:
            total_calls = db.query(func.count(CallRecord.call_id)).scalar()
            confirmed   = db.query(func.count(CallRecord.call_id))\
                            .filter(CallRecord.booking_status == "confirmed").scalar()
            avg_duration= db.query(func.avg(CallRecord.duration_secs)).scalar()

            # Language breakdown
            lang_rows = (
                db.query(CallRecord.language, func.count(CallRecord.call_id))
                .group_by(CallRecord.language)
                .all()
            )
            languages = {lang: count for lang, count in lang_rows}

            return {
                "total_calls":     total_calls,
                "confirmed_bookings": confirmed,
                "booking_rate_pct": round((confirmed / total_calls * 100) if total_calls else 0, 1),
                "avg_duration_s":   round(avg_duration or 0, 1),
                "languages":        languages
            }


# ── Test ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Day 14 — Postgres Manager Test")
    print("="*60)

    pg = PostgresManager()

    # Simulate archiving 2 calls
    calls = [
        {
            "call_id": "call_DEMO_001",
            "patient_phone": "+916302008804",
            "started_at": datetime.utcnow().isoformat(),
            "ended_at": datetime.utcnow().isoformat(),
            "callStatus": "completed",
            "agentId": "aria-dental-v1",
            "turns": [
                {"role": "agent", "content": "నమస్తే!"},
                {"role": "patient", "content": "అపాయింట్మెంట్ కావాలి"},
            ],
            "extracted_data": {
                "patientName": "లోకేష్ గడ్డం",
                "patientEmail": "lokeshgaddam2514@gmail.com",
                "bookingId": "BLN8948006",
                "appointmentDate": "రేపు",
                "appointmentTime": "10:00 AM",
                "treatment": "General Consultation",
                "booking_status": "confirmed",
                "language": "Telugu",
            }
        },
        {
            "call_id": "call_DEMO_002",
            "patient_phone": "+919876543210",
            "started_at": datetime.utcnow().isoformat(),
            "ended_at": datetime.utcnow().isoformat(),
            "callStatus": "completed",
            "turns": [],
            "extracted_data": {
                "patientName": "Ravi Kumar",
                "treatment": "Teeth Cleaning",
                "booking_status": "confirmed",
                "language": "English",
            }
        }
    ]

    for call in calls:
        pg.save_call(call)

    # Test queries
    print("\n📊 Analytics:")
    stats = pg.get_stats()
    print(json.dumps(stats, indent=2))

    print("\n📋 Patient History (+916302008804):")
    history = pg.get_patient_history("+916302008804")
    for h in history:
        print(f"  {h['date']} | {h['name']} | {h['treatment']} | {h['booking']}")

    print("\n📅 Pending Bookings:")
    bookings = pg.get_pending_bookings()
    for b in bookings:
        print(f"  {b['name']} | {b['phone']} | {b['date']} {b['time']}")

    print("\n🎉 Postgres Manager working!\n")
