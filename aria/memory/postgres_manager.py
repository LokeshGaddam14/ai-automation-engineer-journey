"""
Aria — Postgres Persistent Storage
=====================================
Durable, long-term storage for completed call records using SQLAlchemy.

Uses Supabase (free hosted Postgres) or falls back to SQLite for development.
Sign up FREE at: https://supabase.com/ → New Project → Copy Connection String

Architecture:
    ACTIVE CALL  → Redis (real-time, <1ms)
    CALL ENDS    → Redis session → Postgres (durable archive)
    ANALYTICS    → Postgres SQL queries
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import (
    Column, DateTime, Integer, JSON, String, Text, Boolean,
    create_engine, func, text
)
from sqlalchemy.orm import DeclarativeBase, Session

# Auto-load .env
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass

# ── Config ─────────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./aria_calls.db"  # SQLite fallback — zero setup!
)


# ── ORM Models ─────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class CallRecord(Base):
    """Persistent record for a completed call."""
    __tablename__ = "call_records"

    call_id          = Column(String(100), primary_key=True)
    patient_phone    = Column(String(20),  nullable=False, index=True)
    started_at       = Column(DateTime,    default=datetime.utcnow)
    ended_at         = Column(DateTime,    nullable=True)
    duration_secs    = Column(Integer,     nullable=True)
    language         = Column(String(20),  default="English")
    agent_id         = Column(String(100), nullable=True)
    call_status      = Column(String(50),  default="completed")

    # Extracted booking info
    patient_name     = Column(String(100), nullable=True)
    patient_email    = Column(String(200), nullable=True)
    booking_id       = Column(String(50),  nullable=True)
    appointment_date = Column(String(100), nullable=True)
    appointment_time = Column(String(50),  nullable=True)
    treatment        = Column(String(200), nullable=True)
    booking_status   = Column(String(50),  default="pending")

    # Smart Features Flags
    reminder_sent    = Column(Boolean, default=False)
    followup_sent    = Column(Boolean, default=False)

    # Full data as JSON (flexible, no schema changes needed)
    extracted_data   = Column(JSON, default=dict)
    turns            = Column(JSON, default=list)
    summary          = Column(Text, nullable=True)

    created_at       = Column(DateTime, server_default=func.now())


class AppointmentReminder(Base):
    """Track reminders sent to patients (avoids duplicates)."""
    __tablename__ = "appointment_reminders"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    call_id       = Column(String(100), nullable=False)
    patient_phone = Column(String(20),  nullable=False)
    channel       = Column(String(20),  nullable=False)  # email/whatsapp/sms
    sent_at       = Column(DateTime,    default=datetime.utcnow)
    status        = Column(String(20),  default="sent")


# ── Manager Class ──────────────────────────────────────────────────────────────

class PostgresManager:
    """
    Durable storage for completed call records.

    Usage:
        pg = PostgresManager()
        pg.save_call(redis_session_dict)
        pg.get_patient_history("+91XXXXXXXXXX")
        pg.get_stats()
    """

    def __init__(self, db_url: str = DATABASE_URL):
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        self.engine = create_engine(db_url, connect_args=connect_args)
        Base.metadata.create_all(self.engine)

        # Simple auto-migration for SQLite/Postgres since we don't have Alembic
        try:
            with self.engine.begin() as conn:
                conn.execute(text("ALTER TABLE call_records ADD COLUMN reminder_sent BOOLEAN DEFAULT FALSE;"))
        except Exception:
            pass
        try:
            with self.engine.begin() as conn:
                conn.execute(text("ALTER TABLE call_records ADD COLUMN followup_sent BOOLEAN DEFAULT FALSE;"))
        except Exception:
            pass

        db_type = "SQLite" if db_url.startswith("sqlite") else \
                  "Supabase" if "supabase" in db_url else "PostgreSQL"
        print(f"[OK] PostgresManager initialized (DB: {db_type})")

    # ── Write operations ───────────────────────────────────────────────────────

    def save_call(self, session_dict: Dict) -> str:
        """
        Archive a completed Redis session to Postgres.

        Args:
            session_dict: Final session from RedisSessionManager.end_session()

        Returns: call_id of saved record
        """
        with Session(self.engine) as db:
            started = datetime.fromisoformat(
                session_dict.get("started_at", datetime.utcnow().isoformat())
            )
            ended_str = session_dict.get("ended_at")
            ended = datetime.fromisoformat(ended_str) if ended_str else datetime.utcnow()
            duration = max(0, int((ended - started).total_seconds()))

            extracted = session_dict.get("extracted_data", {})

            record = CallRecord(
                call_id          = session_dict["call_id"],
                patient_phone    = session_dict.get("patient_phone", ""),
                started_at       = started,
                ended_at         = ended,
                duration_secs    = duration,
                language         = extracted.get("language", "English"),
                agent_id         = session_dict.get("agentId", ""),
                call_status      = session_dict.get("callStatus", "completed"),
                patient_name     = extracted.get("patientName") or extracted.get("name", ""),
                patient_email    = extracted.get("patientEmail") or extracted.get("email", ""),
                booking_id       = extracted.get("bookingId", ""),
                appointment_date = extracted.get("appointmentDate", ""),
                appointment_time = extracted.get("appointmentTime", ""),
                treatment        = extracted.get("treatment", ""),
                booking_status   = extracted.get("booking_status", "pending"),
                extracted_data   = extracted,
                turns            = session_dict.get("turns", []),
                summary          = extracted.get("summary", ""),
            )

            # Upsert (handle duplicates gracefully)
            existing = db.get(CallRecord, session_dict["call_id"])
            if existing:
                db.delete(existing)
                db.flush()

            db.add(record)
            db.commit()
            print(f"[Archive] Call archived: {record.call_id} | Duration: {duration}s")
            return record.call_id

    def create_direct_booking(self, name: str, phone: str, date: str, time: str, treatment: str, booking_id: str, status: str = "confirmed") -> str:
        """Create a direct booking record (e.g. from external API like Bolna)."""
        import uuid
        call_id = f"ext_{uuid.uuid4().hex[:12]}"
        session_dict = {
            "call_id": call_id,
            "patient_phone": phone,
            "started_at": datetime.utcnow().isoformat(),
            "ended_at": datetime.utcnow().isoformat(),
            "extracted_data": {
                "name": name,
                "phone": phone,
                "appointmentDate": date,
                "appointmentTime": time,
                "treatment": treatment,
                "bookingId": booking_id,
                "booking_status": status,
                "summary": f"Direct booking created via external receptionist."
            }
        }
        return self.save_call(session_dict)

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
            "I see you called us before. Is this about your previous appointment?"
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
                    "call_id":          r.call_id,
                    "date":             r.started_at.strftime("%Y-%m-%d"),
                    "duration_seconds": r.duration_secs,
                    "duration_s":       r.duration_secs,   # legacy alias
                    "name":             r.patient_name,
                    "treatment":        r.treatment,
                    "booking_status":   r.booking_status,
                    "booking":          r.booking_status,  # legacy alias
                    "language":         r.language,
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
                "call_id":    r.call_id,
                "patient":    r.patient_phone,
                "name":       r.patient_name,
                "duration_s": r.duration_secs,
                "language":   r.language,
                "booking_id": r.booking_id,
                "treatment":  r.treatment,
                "date":       r.appointment_date,
                "time":       r.appointment_time,
                "booking":    r.booking_status,
                "summary":    r.summary,
                "turns":      r.turns,
                "extracted":  r.extracted_data,
            }

    def get_pending_bookings(self) -> List[Dict]:
        """Get confirmed bookings (for reminder sending)."""
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

    def search_calls(self, query: str, limit: int = 20) -> List[Dict]:
        """Search call records by patient name or phone."""
        with Session(self.engine) as db:
            records = (
                db.query(CallRecord)
                .filter(
                    (CallRecord.patient_name.ilike(f"%{query}%")) |
                    (CallRecord.patient_phone.ilike(f"%{query}%"))
                )
                .order_by(CallRecord.started_at.desc())
                .limit(limit)
                .all()
            )
            return [self.get_call(r.call_id) for r in records if r]

    def get_stats(self) -> Dict:
        """
        Analytics summary — for dashboard and reporting.
        Returns call counts, booking rates, language breakdown.
        Field names are aliased to match the React dashboard frontend.
        """
        with Session(self.engine) as db:
            total_calls  = db.query(func.count(CallRecord.call_id)).scalar() or 0
            confirmed    = db.query(func.count(CallRecord.call_id))\
                            .filter(CallRecord.booking_status == "confirmed").scalar() or 0
            avg_duration = db.query(func.avg(CallRecord.duration_secs)).scalar() or 0
            total_duration = db.query(func.sum(CallRecord.duration_secs)).scalar() or 0
            unique_patients = db.query(func.count(func.distinct(CallRecord.patient_phone))).scalar() or 0

            lang_rows = (
                db.query(CallRecord.language, func.count(CallRecord.call_id))
                .group_by(CallRecord.language)
                .all()
            )
            languages = {lang: count for lang, count in lang_rows}

            booking_rate = round(confirmed / total_calls, 3) if total_calls else 0

            # Treatment mix
            treatment_rows = (
                db.query(CallRecord.treatment, func.count(CallRecord.call_id))
                .filter(CallRecord.treatment != None, CallRecord.treatment != "")
                .group_by(CallRecord.treatment)
                .order_by(func.count(CallRecord.call_id).desc())
                .limit(8)
                .all()
            )
            treatments = [{"treatment": t, "count": c} for t, c in treatment_rows]

            # Daily calls (last 7 days using naive string grouping for cross-db compatibility)
            # A simple group_by on the date prefix
            daily_rows = (
                db.query(func.substr(CallRecord.started_at, 1, 10).label('day'), func.count(CallRecord.call_id))
                .group_by('day')
                .order_by('day')
                .limit(7)
                .all()
            )
            daily_calls = [{"date": d, "count": c} for d, c in daily_rows]

            return {
                # Frontend-compatible names
                "total_calls":            total_calls,
                "confirmed_bookings":     confirmed,
                "avg_duration_seconds":   round(float(avg_duration), 1),
                "total_duration_seconds": round(float(total_duration), 1),
                "unique_patients":        unique_patients,
                "booking_rate":           booking_rate,
                "languages":              languages,
                "treatments":             treatments,
                "by_date":                daily_calls,
                # Legacy names (keep for backwards compat)
                "booking_rate_pct":       round(booking_rate * 100, 1),
                "avg_duration_s":         round(float(avg_duration), 1),
            }

    def list_all_calls(self, limit: int = 50) -> List[Dict]:
        """List all call records, most recent first."""
        with Session(self.engine) as db:
            records = (
                db.query(CallRecord)
                .order_by(CallRecord.started_at.desc())
                .limit(limit)
                .all()
            )
            return [self._record_to_dict(r) for r in records]

    def _record_to_dict(self, r) -> Dict:
        """Convert a CallRecord ORM row to a dashboard-compatible dict."""
        return {
            "call_id":        r.call_id,
            "patient_phone":  r.patient_phone,
            "started_at":     r.started_at.isoformat() if r.started_at else None,
            "ended_at":       r.ended_at.isoformat() if r.ended_at else None,
            "duration_seconds": r.duration_secs,
            "name":           r.patient_name,
            "booking_status": r.booking_status or "pending",
            "treatment":      r.treatment,
            "turns":          r.turns or [],
            "extracted_data": r.extracted_data or {},
        }

