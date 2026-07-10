# -*- coding: utf-8 -*-
"""
Day 11/13 Helper - Auto Update ngrok URL in Env & Bolna
======================================================
Retrieves the active ngrok URL from your local ngrok agent,
updates .env, and registers the webhook/LLM URL with Bolna AI.
"""

import os
import re
import requests
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(ENV_PATH)

BOLNA_API_KEY = os.getenv("BOLNA_API_KEY")
BOLNA_AGENT_ID = os.getenv("BOLNA_AGENT_ID")

def get_ngrok_url():
    try:
        resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
        resp.raise_for_status()
        tunnels = resp.json().get("tunnels", [])
        for tunnel in tunnels:
            if tunnel.get("proto") == "https":
                return tunnel.get("public_url")
    except Exception as e:
        print(f"[ERROR] Could not connect to local ngrok API (127.0.0.1:4040): {e}")
        print("   Make sure ngrok is running in a terminal tab.")
    return None

def update_env_file(new_url):
    if not os.path.exists(ENV_PATH):
        print(f"[ERROR] .env file not found at {ENV_PATH}")
        return False

    with open(ENV_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace NGROK_URL value
    if "NGROK_URL=" in content:
        content = re.sub(r"NGROK_URL=.*", f"NGROK_URL={new_url}", content)
    else:
        content += f"\nNGROK_URL={new_url}"

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] Updated NGROK_URL in .env to: {new_url}")
    return True

def update_bolna_agent(new_url):
    if not BOLNA_API_KEY or not BOLNA_AGENT_ID:
        print("[WARN] Bolna API Key or Agent ID missing in .env. Skipping Bolna update.")
        return

    headers = {
        "Authorization": f"Bearer {BOLNA_API_KEY}",
        "Content-Type": "application/json"
    }

    url = f"https://api.bolna.ai/v2/agent/{BOLNA_AGENT_ID}"
    
    try:
        # Fetch current configuration first
        get_resp = requests.get(url, headers=headers, timeout=10)
        if get_resp.status_code != 200:
            print(f"[ERROR] Failed to fetch Bolna agent: {get_resp.status_code}")
            return

        agent_data = get_resp.json()
        agent_config = agent_data.get("agent_config", {})

        # Update the Webhook URL in task config if it exists
        webhook_updated = False
        
        # 1. Update general tasks webhook
        tasks = agent_config.get("tasks", [])
        for task in tasks:
            task_config = task.get("task_config", {})
            # If agent has a webhook block or api endpoints
            if "webhook" in task_config:
                task_config["webhook"] = f"{new_url}/bolna/webhook"
                webhook_updated = True

        # 2. Update webhook under agent_config if present
        if "webhook_url" in agent_config:
            agent_config["webhook_url"] = f"{new_url}/bolna/webhook"
            webhook_updated = True

        # Send full PUT update to Bolna
        payload = {
            "agent_config": agent_config,
            "agent_prompts": agent_data.get("agent_prompts", {})
        }

        put_resp = requests.put(url, headers=headers, json=payload, timeout=15)
        if put_resp.status_code in (200, 204):
            print("[OK] Successfully updated webhook URL in Bolna agent.")
        else:
            print(f"[WARN] Bolna API returned status {put_resp.status_code}: {put_resp.text}")

    except Exception as e:
        print(f"[ERROR] Error communicating with Bolna API: {e}")

if __name__ == "__main__":
    print("[INFO] Checking ngrok status...")
    url = get_ngrok_url()
    if url:
        update_env_file(url)
        update_bolna_agent(url)
    else:
        print("[ERROR] Could not update configuration. Please ensure ngrok is active.")
