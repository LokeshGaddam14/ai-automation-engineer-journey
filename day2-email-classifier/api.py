from fastapi import FastAPI
from pydantic import BaseModel
from langchain_groq import ChatGroq
import os, json
from dotenv import load_dotenv

load_dotenv()

# Create FastAPI app
app = FastAPI()

# Connect to Groq
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant"
)

# Define what data FastAPI expects from n8n
class EmailRequest(BaseModel):
    subject: str
    body: str
    sender: str

# The endpoint n8n will call
@app.post("/classify")
def classify_email(email: EmailRequest):
    prompt = f"""
    Classify this email and return ONLY JSON:
    Subject: {email.subject}
    Body: {email.body}
    
    Return exactly:
    {{"category": "billing/appointment/complaint/technical/general", 
      "urgency": "high/medium/low", 
      "summary": "one line summary"}}
    """
    response = llm.invoke(prompt)
    try:
        result = json.loads(response.content)
    except:
        result = {"category": "unknown", "urgency": "low", "summary": "parsing failed"}
    
    return result