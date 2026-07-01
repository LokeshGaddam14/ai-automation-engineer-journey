import pandas as pd
from langchain_groq import ChatGroq
import os
import json
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()

# Connect to Groq AI
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant"  # free model
)

# Read the CSV
script_dir = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(script_dir, "emails.csv"))

# Loop through each email
results = []
for index, row in df.iterrows():
    
    # Build the prompt — fill subject and body from each row
    prompt = f"""
    Classify this email and return ONLY JSON nothing else:
    
    Subject: {row['subject']}
    Body: {row['body']}
    
    Return exactly this format:
    {{"category": "billing/appointment/complaint/technical/general", "urgency": "high/medium/low", "summary": "one line summary"}}
    """
    
    # Send to Groq AI and get response
    response = llm.invoke(prompt)
    
    # Parse the JSON response
    try:
        result = json.loads(response.content)
    except:
        result = {"category": "unknown", "urgency": "low", "summary": "parsing failed"}
    
    # Add original email data + AI result together
    results.append({
        "subject": row["subject"],
        "sender": row["sender"],
        "body": row["body"],
        "timestamp": row["timestamp"],
        "category": result.get("category"),
        "urgency": result.get("urgency"),
        "summary": result.get("summary")
    })
    
    print(f"[OK] Classified: {row['subject']} -> {result.get('category')} | {result.get('urgency')}")

# Save results to new CSV
output_df = pd.DataFrame(results)
output_file = os.path.join(script_dir, "classified_emails.csv")
output_df.to_csv(output_file, index=False)
print(f"\n[OK] Done! Results saved to {output_file}")