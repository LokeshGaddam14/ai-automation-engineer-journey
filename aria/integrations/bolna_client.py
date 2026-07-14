"""
Bolna Voice Integration for Aria - Day 19

Bolna is an Indian voice AI platform. This module handles:
- Voice call webhooks
- Real-time transcript updates
- Call recording management
- Voice quality metrics
"""

import os
import hmac
import hashlib
import requests
import json
from typing import Dict, Optional, List
from datetime import datetime


class BolnaClient:
    """Integration with Bolna voice platform for Indian phone numbers."""

    def __init__(self):
        self.api_key = os.getenv("BOLNA_API_KEY", "demo_key")
        self.api_url = "https://api.bolna.dev/v1"
        self.webhook_url = os.getenv(
            "BOLNA_WEBHOOK_URL",
            "http://localhost:8000/webhooks/bolna"
        )
        self.agent_id = os.getenv("BOLNA_AGENT_ID", "")

    def create_agent(self, agent_name: str, voice_id: str = "hindi-female") -> Dict:
        """
        Create a Bolna voice agent.

        Args:
            agent_name: Name of the agent (e.g., "Aria Dental Receptionist")
            voice_id: Voice type — hindi-female, hindi-male,
                      english-female, english-male, gujarati-female, gujarati-male

        Returns:
            Agent details with agent_id
        """
        payload = {
            "agent_name": agent_name,
            "voice": voice_id,
            "language": "hi",          # Hindi by default
            "webhook_url": self.webhook_url,
            "max_call_duration": 3600,
            "conversation_type": "inbound",
            "enable_recordings": True,
            "enable_transcripts": True,
        }
        try:
            response = requests.post(
                f"{self.api_url}/agents",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
            print(f"[OK] Agent created: {result.get('agent_id')}")
            return result
        except Exception as e:
            print(f"[Error] Error creating agent: {e}")
            return {"error": str(e), "status": "failed"}

    def get_agent(self, agent_id: str) -> Dict:
        """Retrieve agent details."""
        try:
            response = requests.get(
                f"{self.api_url}/agents/{agent_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error retrieving agent: {e}")
            return {}

    def get_call_recording(self, call_id: str) -> Optional[str]:
        """
        Get call recording URL.

        Returns:
            URL to download the recording, or None on failure.
        """
        try:
            response = requests.get(
                f"{self.api_url}/calls/{call_id}/recording",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("recording_url")
        except Exception as e:
            print(f"❌ Error retrieving recording: {e}")
            return None

    def get_call_transcript(self, call_id: str) -> Dict:
        """
        Get full call transcript.

        Returns:
            Dict with turns: [{"role": "agent|user", "text": "...", "timestamp": "..."}]
        """
        try:
            response = requests.get(
                f"{self.api_url}/calls/{call_id}/transcript",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error retrieving transcript: {e}")
            return {"turns": []}

    def get_call_metrics(self, call_id: str) -> Dict:
        """
        Get call quality metrics.

        Returns:
            Dict with audio_quality, latency_ms, bandwidth_mbps, etc.
        """
        try:
            response = requests.get(
                f"{self.api_url}/calls/{call_id}/metrics",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error retrieving metrics: {e}")
            return {
                "audio_quality": "unknown",
                "latency_ms": 0,
                "bandwidth_mbps": 0.0,
            }

    def validate_webhook_signature(self, request_data: str, signature: str) -> bool:
        """Validate HMAC-SHA256 webhook signature from Bolna."""
        try:
            expected = hmac.new(
                self.api_key.encode(),
                request_data.encode(),
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(signature, expected)
        except Exception as e:
            print(f"❌ Error validating signature: {e}")
            return False


# ── WebSocket connection manager for broadcasting ──────────────────────────────

class WebSocketManager:
    """Manage WebSocket connections for live dashboard updates."""

    def __init__(self):
        self.active_connections: List = []

    async def connect(self, websocket) -> None:
        """Add a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[OK] Dashboard client connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"❌ Dashboard client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict) -> None:
        """Broadcast message to all connected clients."""
        dead: List = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"❌ Error broadcasting: {e}")
                dead.append(connection)
        for connection in dead:
            await self.disconnect(connection)


# ── Singletons ─────────────────────────────────────────────────────────────────

bolna_client = BolnaClient()
ws_manager   = WebSocketManager()


# ── Mock data for testing ──────────────────────────────────────────────────────

def get_mock_active_calls() -> List[Dict]:
    """Return mock active calls for testing when Bolna is not connected."""
    return [
        {
            "call_id":       "call_001",
            "patient_phone": "+916302008804",
            "started_at":    datetime.now().isoformat(),
            "duration":      145,
            "status":        "active",
            "transcript": [
                {
                    "role":      "agent",
                    "text":      "Hello! Welcome to Naveen Advanced Dental Clinic. How can I help you today?",
                    "timestamp": datetime.now().isoformat(),
                },
                {
                    "role":      "patient",
                    "text":      "Hi, I'd like to book an appointment for a checkup.",
                    "timestamp": datetime.now().isoformat(),
                },
                {
                    "role":      "agent",
                    "text":      "Of course! When would you like to come in? I can check available slots.",
                    "timestamp": datetime.now().isoformat(),
                },
            ],
            "quality": {
                "audio_quality":  "good",
                "latency_ms":     45,
                "bandwidth_mbps": 0.85,
            },
        }
    ]
