"""
Aria — Redis Session Manager
=============================
Real-time, in-memory session state for active Bolna voice calls.

Uses Upstash Redis (free cloud Redis — no local Redis server needed).
Sign up FREE at: https://upstash.com/ → Create a Redis database → Get REST URL + Token

Why Redis for voice calls?
- Ultra-low latency (<1ms) for real-time reads/writes during a call
- Auto-expiry (TTL) → sessions clean themselves up after call ends
- Patient calls back within 1 hour → agent remembers name, complaint, etc.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Auto-load .env from project root (works from any subdirectory)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass

# Try local Redis first, fall back to Upstash REST client
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# ── Config (loaded from .env) ──────────────────────────────────────────────────
REDIS_URL                = os.getenv("REDIS_URL", "redis://localhost:6379")
UPSTASH_REDIS_REST_URL   = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
SESSION_TTL              = int(os.getenv("REDIS_SESSION_TTL", 3600))  # 1 hour


class RedisSessionManager:
    """
    Real-time session memory for active voice calls.

    Stores per-call state in Redis with auto-expiry.
    Supports: Upstash cloud Redis, local Redis, in-memory fallback.

    Session schema:
        call_id        str   Unique call identifier (from Bolna)
        patient_phone  str   Patient's phone number
        started_at     str   ISO timestamp call started
        ended_at       str   ISO timestamp call ended
        state          str   Current agent state: greeting/booking/info/escalation
        extracted_data dict  Parsed data: name, date, time, treatment
        turns          list  Full conversation turns [{role, content, timestamp}]
    """

    def __init__(self):
        """Initialize connection — prefers Upstash over local Redis."""
        self.mode = self._init_connection()
        print(f"[OK] RedisSessionManager initialized (mode: {self.mode})")

    def _init_connection(self) -> str:
        """Try Upstash REST → local Redis → in-memory fallback."""
        # Option 1: Upstash (cloud, no local install needed)
        if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
            try:
                from upstash_redis import Redis
                self.client = Redis(
                    url=UPSTASH_REDIS_REST_URL,
                    token=UPSTASH_REDIS_REST_TOKEN
                )
                self.client.ping()
                return "upstash"
            except Exception as e:
                print(f"⚠️  Upstash connection failed: {e}")

        # Option 2: Local Redis
        if REDIS_AVAILABLE:
            try:
                self.client = redis.from_url(REDIS_URL, decode_responses=True)
                self.client.ping()
                return "local_redis"
            except Exception as e:
                print(f"⚠️  Local Redis failed: {e}")

        # Option 3: In-memory dict (fallback for development)
        print("⚠️  No Redis available → using in-memory dict (data lost on restart)")
        self._memory: Dict[str, str] = {}
        self.client = None
        return "in_memory"

    # ── Core CRUD operations ───────────────────────────────────────────────────

    def _set(self, key: str, value: str, ttl: int = SESSION_TTL):
        """Set key with TTL (handles all modes)."""
        if self.mode == "in_memory":
            self._memory[key] = value
        else:
            self.client.setex(key, ttl, value)

    def _get(self, key: str) -> Optional[str]:
        """Get key value (handles all modes)."""
        if self.mode == "in_memory":
            return self._memory.get(key)
        return self.client.get(key)

    def _delete(self, key: str):
        """Delete key (handles all modes)."""
        if self.mode == "in_memory":
            self._memory.pop(key, None)
        else:
            self.client.delete(key)

    # ── Session lifecycle ──────────────────────────────────────────────────────

    def start_session(self, call_id: str, patient_phone: str) -> Dict:
        """
        Initialize a new call session in Redis.
        Called when Bolna starts a call (or webhook fires).
        """
        session = {
            "call_id": call_id,
            "patient_phone": patient_phone,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
            "state": "greeting",
            "extracted_data": {},
            "turns": []
        }
        self._set(f"session:{call_id}", json.dumps(session))
        print(f"📞 Session started: {call_id} | Phone: {patient_phone}")
        return session

    def get_session(self, call_id: str) -> Optional[Dict]:
        """
        Retrieve an active session.
        Returns None if session expired or doesn't exist.
        """
        data = self._get(f"session:{call_id}")
        return json.loads(data) if data else None

    def update_session(self, call_id: str, updates: Dict) -> Dict:
        """
        Merge partial updates into the session (non-destructive).

        Example:
            update_session("call_001", {"state": "booking", "extracted_data": {"name": "Ravi"}})
        """
        session = self.get_session(call_id)
        if not session:
            raise ValueError(f"Session '{call_id}' not found or expired")

        # Deep merge extracted_data
        if "extracted_data" in updates and isinstance(updates["extracted_data"], dict):
            session["extracted_data"].update(updates.pop("extracted_data"))

        session.update(updates)
        self._set(f"session:{call_id}", json.dumps(session))
        return session

    def append_turn(
        self,
        call_id: str,
        role: str,
        content: str,
        extracted_data: Optional[Dict] = None
    ):
        """
        Log a conversation turn (agent or patient message).

        Args:
            role:           "agent" | "patient" | "system"
            content:        The spoken text
            extracted_data: Any data extracted from this turn
        """
        session = self.get_session(call_id)
        if not session:
            return

        turn = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if extracted_data:
            turn["extracted_data"] = extracted_data

        session["turns"].append(turn)
        self._set(f"session:{call_id}", json.dumps(session))

    def end_session(self, call_id: str) -> Optional[Dict]:
        """
        Finalize a session and remove it from Redis.

        The caller should persist the returned session to Postgres
        before discarding it.

        Returns: Final session dict (None if not found)
        """
        session = self.get_session(call_id)
        if session:
            session["ended_at"] = datetime.now(timezone.utc).isoformat()
            self._delete(f"session:{call_id}")
            print(f"📴 Session ended: {call_id} | Turns: {len(session['turns'])}")
        return session

    def get_patient_recent_session(self, patient_phone: str) -> Optional[Dict]:
        """
        Look for any active session for a phone number.
        Useful when a patient calls back within the same hour.
        """
        if self.mode == "in_memory":
            for key, val in self._memory.items():
                if key.startswith("session:"):
                    session = json.loads(val)
                    if session.get("patient_phone") == patient_phone:
                        return session
        return None

    # ── Utility ───────────────────────────────────────────────────────────────

    def session_exists(self, call_id: str) -> bool:
        """Check if a session is still alive."""
        return self.get_session(call_id) is not None

    def get_turn_count(self, call_id: str) -> int:
        """Get number of conversation turns."""
        session = self.get_session(call_id)
        return len(session["turns"]) if session else 0
