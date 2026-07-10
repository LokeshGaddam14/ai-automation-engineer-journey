"""
Aria Memory Tests
==================
Tests for Redis session manager.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from aria.memory.redis_manager import RedisSessionManager


@pytest.fixture
def redis_mgr():
    """Create RedisSessionManager in in-memory mode for testing."""
    mgr = RedisSessionManager()
    # Force in-memory mode for tests
    mgr.mode = "in_memory"
    mgr._memory = {}
    mgr.client = None
    return mgr


def test_redis_session_start(redis_mgr):
    session = redis_mgr.start_session("call_001", "+916302008804")
    assert session["call_id"] == "call_001"
    assert session["patient_phone"] == "+916302008804"
    assert session["state"] == "greeting"
    assert session["turns"] == []


def test_redis_session_get(redis_mgr):
    redis_mgr.start_session("call_002", "+91999999")
    session = redis_mgr.get_session("call_002")
    assert session is not None
    assert session["call_id"] == "call_002"


def test_redis_append_turn(redis_mgr):
    redis_mgr.start_session("call_003", "+91111")
    redis_mgr.append_turn("call_003", "agent", "Hello!")
    redis_mgr.append_turn("call_003", "patient", "Book appointment")
    session = redis_mgr.get_session("call_003")
    assert len(session["turns"]) == 2
    assert session["turns"][0]["role"] == "agent"


def test_redis_end_session(redis_mgr):
    redis_mgr.start_session("call_004", "+91222")
    final = redis_mgr.end_session("call_004")
    assert final is not None
    assert final["ended_at"] is not None
    assert redis_mgr.get_session("call_004") is None  # Gone from Redis
