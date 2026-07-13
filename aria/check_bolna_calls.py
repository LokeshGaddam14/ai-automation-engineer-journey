import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOLNA_API_KEY = os.getenv("BOLNA_API_KEY", "")
BOLNA_AGENT_ID = os.getenv("BOLNA_AGENT_ID", "")
BOLNA_BASE_URL = "https://api.bolna.ai"

if not BOLNA_API_KEY:
    print("❌ BOLNA_API_KEY is not set in .env")
    exit(1)

headers = {
    "Authorization": f"Bearer {BOLNA_API_KEY}",
    "Content-Type": "application/json"
}

print(f"Connecting to Bolna API...")
print(f"Agent ID: {BOLNA_AGENT_ID}")

# Try 1: /agent/{agent_id}/executions
url1 = f"{BOLNA_BASE_URL}/agent/{BOLNA_AGENT_ID}/executions"
try:
    print(f"Checking URL: {url1}")
    resp = requests.get(url1, headers=headers)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print("Data:")
        print(resp.json())
except Exception as e:
    print(f"Error checking url1: {e}")

# Try 2: /v2/agent/{agent_id}/executions
url2 = f"{BOLNA_BASE_URL}/v2/agent/{BOLNA_AGENT_ID}/executions"
try:
    print(f"Checking URL: {url2}")
    resp = requests.get(url2, headers=headers)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print("Data:")
        print(resp.json())
except Exception as e:
    print(f"Error checking url2: {e}")

# Try 3: /executions
url3 = f"{BOLNA_BASE_URL}/executions"
try:
    print(f"Checking URL: {url3}")
    resp = requests.get(url3, headers=headers)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print("Data:")
        print(resp.json())
except Exception as e:
    print(f"Error checking url3: {e}")
