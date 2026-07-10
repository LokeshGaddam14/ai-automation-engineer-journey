"""
Day 13 — Bolna AI Webhook Logger
=================================
Standalone FastAPI app that receives Bolna AI call-execution webhooks
and logs call records to call_logs.json.

Bolna sends a POST to your webhook URL (configured in Agent → Analytics tab)
whenever a call changes status. The payload matches the Get Execution API format.

Can be run independently OR the /bolna/webhook and /calls endpoints
can be integrated into day10_fastapi/day10_api.py.

Run standalone (port 8001) if you want to test logging separately:
    python day13_webhook/day13_webhook_logger.py

OR test via the main API (port 8000) — webhook is already there.

Test with PowerShell:
    # Simulate a Bolna call-ended webhook
    $body = '{
      "execution_id": "test-exec-001",
      "agent_id": "your-agent-id-here",
      "call_status": "completed",
      "to_number": "+919876543210",
      "conversation_time": 45,
      "transcript": "Aria: Hi, this is Aria. Patient: How much is a root canal? Aria: It costs between 4000 and 8000 rupees.",
      "summary": "Patient asked about root canal pricing."
    }'
    Invoke-WebRequest -Uri "http://127.0.0.1:8000/bolna/webhook" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing

    # View all logged calls
    Invoke-WebRequest -Uri "http://127.0.0.1:8000/calls" -UseBasicParsing
"""

import os
import json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Aria — Webhook Logger",
    description="Logs Bolna AI call execution events to call_logs.json",
    version="2.0.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CALL_LOG_PATH = os.path.join(BASE_DIR, "call_logs.json")


# ─────────────────────────────────────────────
# Helper: read all logs
# ─────────────────────────────────────────────
def read_logs() -> list:
    if not os.path.exists(CALL_LOG_PATH):
        return []
    with open(CALL_LOG_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


# ─────────────────────────────────────────────
# Helper: append a log entry
# ─────────────────────────────────────────────
def append_log(entry: dict):
    logs = read_logs()
    logs.append(entry)
    with open(CALL_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f"[LOGGER] Saved call {entry.get('call_id', '?')} → {CALL_LOG_PATH}")


# ─────────────────────────────────────────────
# Parse Bolna execution payload
# ─────────────────────────────────────────────
def parse_bolna_payload(body: dict) -> dict:
    """
    Bolna sends execution data matching the Get Execution API format.
    Fields: execution_id, agent_id, call_status, to_number, conversation_time,
            transcript, summary, telephony_data, created_at, etc.
    This normalizes to a flat log entry.
    """
    telephony = body.get("telephony_data", {})

    return {
        "logged_at": datetime.utcnow().isoformat() + "Z",
        "call_id": body.get("execution_id") or body.get("id", "unknown"),
        "event_type": "bolna_execution",
        "call_status": body.get("call_status", "unknown"),
        "phone_number": (
            body.get("to_number")
            or telephony.get("to_number")
            or body.get("from_number", "unknown")
        ),
        "agent_id": body.get("agent_id", "unknown"),
        "created_at": body.get("created_at", ""),
        "duration_seconds": body.get("conversation_time") or body.get("duration"),
        "transcript": body.get("transcript", ""),
        "summary": body.get("summary", ""),
        "telephony_data": telephony,
        "extraction_details": body.get("extraction_details", {}),
        "call_type": body.get("call_type", "inbound"),
    }


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────
@app.get("/")
def root():
    logs = read_logs()
    return {
        "status": "Aria Logger is online",
        "total_calls_logged": len(logs),
        "log_file": CALL_LOG_PATH
    }


@app.post("/bolna/webhook")
async def bolna_webhook(request: Request):
    """
    Receives Bolna AI execution webhook events.
    Bolna POSTs execution data to this endpoint on every call status change.
    Configure this URL in: Bolna Dashboard → Agent → Analytics tab →
      "Push all execution data to webhook"

    Bolna webhook IP to whitelist: 13.203.39.153
    """
    body = await request.json()
    call_status = body.get("call_status", "unknown")
    execution_id = body.get("execution_id", "unknown")

    print(f"[BOLNA WEBHOOK] execution_id={execution_id} status={call_status}")

    # Log all completed/ended calls
    if call_status in ("completed", "failed", "no-answer", "busy", "canceled",
                       "call_completed", "hangup"):
        entry = parse_bolna_payload(body)
        append_log(entry)

        print(f"  Call ID   : {entry['call_id']}")
        print(f"  Status    : {entry['call_status']}")
        print(f"  Duration  : {entry['duration_seconds']}s")
        print(f"  Number    : {entry['phone_number']}")
        if entry.get("summary"):
            print(f"  Summary   : {str(entry['summary'])[:100]}...")

        return JSONResponse({"status": "logged", "call_id": entry["call_id"]})

    # For in-progress or queued status — just acknowledge
    return JSONResponse({"status": "received", "call_status": call_status})


@app.get("/calls")
def get_all_calls():
    """Return all logged call records, newest first."""
    logs = read_logs()
    return {
        "total": len(logs),
        "calls": list(reversed(logs))  # newest first
    }


@app.get("/calls/{call_id}")
def get_call(call_id: str):
    """Return a single call record by call ID."""
    logs = read_logs()
    for entry in logs:
        if entry.get("call_id") == call_id:
            return entry
    return JSONResponse({"error": "Call not found"}, status_code=404)


@app.get("/calls/stats/summary")
def call_stats():
    """Return aggregated stats across all calls."""
    logs = read_logs()
    if not logs:
        return {"total_calls": 0}

    durations = [e["duration_seconds"] for e in logs if e.get("duration_seconds")]
    costs = [e["cost"] for e in logs if e.get("cost") is not None]

    return {
        "total_calls": len(logs),
        "avg_duration_seconds": round(sum(durations) / len(durations), 1) if durations else None,
        "total_cost_usd": round(sum(costs), 4) if costs else None,
        "ended_reasons": _count(logs, "ended_reason"),
        "by_date": _by_date(logs),
    }


def _count(logs: list, key: str) -> dict:
    counts = {}
    for e in logs:
        v = e.get(key, "unknown")
        counts[v] = counts.get(v, 0) + 1
    return counts


def _by_date(logs: list) -> dict:
    by_date = {}
    for e in logs:
        ts = e.get("logged_at", "")
        date = ts[:10] if ts else "unknown"
        by_date[date] = by_date.get(date, 0) + 1
    return by_date


@app.delete("/calls")
def clear_calls():
    """Clear all call logs (dev/testing only)."""
    if os.path.exists(CALL_LOG_PATH):
        with open(CALL_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
    return {"status": "cleared"}


# ─────────────────────────────────────────────
# Run standalone (port 8001)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n🦷 Aria — Day 13: Webhook Logger (Bolna AI)")
    print(f"   Logs will be saved to: {CALL_LOG_PATH}")
    print("   Endpoints:")
    print("     GET  /              → status")
    print("     POST /bolna/webhook → receive Bolna AI execution events")
    print("     GET  /calls         → all call logs")
    print("     GET  /calls/{id}    → single call")
    print("     GET  /calls/stats/summary → aggregated stats")
    print("     DELETE /calls       → clear logs")
    print("")
    print("   Set this URL in Bolna Dashboard → Agent → Analytics tab:")
    print("     <your-ngrok-url>/bolna/webhook")
    print("   Bolna webhook IP: 13.203.39.153 (whitelist if needed)\n")
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
