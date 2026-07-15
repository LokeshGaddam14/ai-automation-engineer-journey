"""
Fetch real call logs from Bolna AI API and sync to local database.
"""
import os
import json
import sqlite3
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BOLNA_API_KEY = os.getenv("BOLNA_API_KEY", "")
BOLNA_AGENT_ID = os.getenv("BOLNA_AGENT_ID", "")
API_URL = "https://api.bolna.dev"

headers = {
    "Authorization": f"Bearer {BOLNA_API_KEY}",
    "Content-Type": "application/json",
}

print(f"Bolna API Key: {BOLNA_API_KEY[:10]}...")
print(f"Bolna Agent ID: {BOLNA_AGENT_ID}")
print()

# Try fetching executions/calls from Bolna
endpoints_to_try = [
    f"{API_URL}/v2/agent/{BOLNA_AGENT_ID}/executions",
    f"{API_URL}/v1/agent/{BOLNA_AGENT_ID}/executions",
    f"{API_URL}/v2/executions?agent_id={BOLNA_AGENT_ID}",
    f"{API_URL}/v1/executions?agent_id={BOLNA_AGENT_ID}",
    f"{API_URL}/v2/calls?agent_id={BOLNA_AGENT_ID}",
    f"{API_URL}/v1/calls",
    f"{API_URL}/v2/agents/{BOLNA_AGENT_ID}/calls",
    f"{API_URL}/v1/agents",
]

for endpoint in endpoints_to_try:
    print(f"Trying: {endpoint}")
    try:
        r = requests.get(endpoint, headers=headers, timeout=10)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Response keys: {list(data.keys()) if isinstance(data, dict) else f'List of {len(data)} items'}")
            print(f"  Data preview: {json.dumps(data, indent=2)[:500]}")
            print("  ✅ SUCCESS!")
            break
        else:
            print(f"  Body: {r.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")
    print()
