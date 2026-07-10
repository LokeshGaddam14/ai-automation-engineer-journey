import os
import sys
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Annotated, TypedDict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

load_dotenv()

app = FastAPI(
    title="Aria - Dental Clinic AI Assistant",
    description="AI voice receptionist for Naveen Advanced Dental Clinic",
    version="1.1.0"
)

# ─────────────────────────────────────────────
# Middleware: bypass ngrok browser warning for all external callers (e.g. Bolna)
# ─────────────────────────────────────────────
@app.middleware("http")
async def add_ngrok_skip_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

# ─────────────────────────────────────────────
# RAG Setup
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAQ_PATH = os.path.join(BASE_DIR, "..", "day05_rag_chromadb", "clinic_faq.txt")

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
loader = TextLoader(FAQ_PATH)
documents = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
chunks = splitter.split_documents(documents)
vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

# ─────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────
@tool
def check_appointment_availability(date: str) -> str:
    """Check available appointment slots for a given date (format: YYYY-MM-DD)."""
    mock_slots = {
        "2026-07-08": ["11:00 AM", "3:00 PM"],
        "2026-07-09": ["10:00 AM", "2:00 PM", "4:30 PM"],
        "2026-07-10": ["9:30 AM", "11:00 AM"],
        "2026-07-11": ["10:30 AM", "3:00 PM"],
        "2026-07-12": ["9:00 AM", "1:00 PM"],
    }
    slots = mock_slots.get(date, ["No slots available for this date, please try another"])
    return f"Available slots for {date}: {', '.join(slots)}"

@tool
def book_appointment(name: str, date: str, time: str) -> str:
    """Book a dental appointment. Requires patient name, date (YYYY-MM-DD), and time."""
    return f"Appointment confirmed for {name} on {date} at {time}. You'll receive a confirmation shortly."

tools = [check_appointment_availability, book_appointment]
llm_with_tools = llm.bind_tools(tools)
tools_map = {t.name: t for t in tools}

# ─────────────────────────────────────────────
# Per-call Session Memory
# ─────────────────────────────────────────────
session_store: dict[str, InMemoryChatMessageHistory] = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in session_store:
        session_store[session_id] = InMemoryChatMessageHistory()
    return session_store[session_id]

# ─────────────────────────────────────────────
# LangGraph State
# ─────────────────────────────────────────────
class AriaState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str
    response: str

# ─────────────────────────────────────────────
# Graph Nodes
# ─────────────────────────────────────────────
def classify_node(state: AriaState) -> AriaState:
    last_message = state["messages"][-1].content
    prompt = (
        "Classify this dental clinic patient message into exactly one of: "
        "booking, pricing, emergency, general.\n"
        "Reply with just the single word.\n"
        f"Message: {last_message}"
    )
    result = llm.invoke(prompt)
    raw = result.content.strip().lower()

    if "book" in raw or "appointment" in raw or "schedul" in raw or "slot" in raw:
        intent = "booking"
    elif "pric" in raw or "cost" in raw or "fee" in raw or "charge" in raw:
        intent = "pricing"
    elif "emerg" in raw:
        intent = "emergency"
    else:
        intent = "general"

    print(f"[CLASSIFIER] intent={intent}")
    return {"intent": intent}


def rag_node(state: AriaState) -> AriaState:
    last_message = state["messages"][-1].content
    docs = retriever.invoke(last_message)
    context = "\n\n".join(d.page_content for d in docs)
    prompt = (
        "You are Aria, a friendly AI receptionist for Naveen Advanced Dental Clinic.\n"
        "Answer using ONLY the context below. If the answer isn't in the context, "
        "say you don't have that information and suggest calling the clinic.\n"
        "Keep answers short and natural — this is a voice call, not a chat.\n\n"
        f"Context:\n{context}\n\n"
        f"Patient: {last_message}"
    )
    result = llm.invoke(prompt)
    print(f"[RAG] responding")
    return {
        "messages": [AIMessage(content=result.content)],
        "response": result.content
    }


def tool_agent_node(state: AriaState) -> AriaState:
    from datetime import date
    today = date.today().isoformat()
    messages = [
        SystemMessage(content=(
            f"You are Aria, a friendly AI receptionist for Naveen Advanced Dental Clinic.\n"
            f"Today's date is {today}. Use this to resolve relative dates like 'tomorrow' or 'next week'.\n"
            "Help patients check availability and book appointments.\n"
            "After getting tool results, relay them clearly and naturally.\n"
            "Never make another tool call after a booking is confirmed.\n"
            "Keep responses short and natural — this is a voice call."
        )),
        *state["messages"]
    ]
    for _ in range(5):
        ai_response = llm_with_tools.invoke(messages)
        messages.append(ai_response)
        if not ai_response.tool_calls:
            print(f"[TOOL_AGENT] done")
            return {
                "messages": [AIMessage(content=ai_response.content)],
                "response": ai_response.content
            }
        for tc in ai_response.tool_calls:
            result = tools_map[tc["name"]].invoke(tc["args"])
            print(f"[TOOL] {tc['name']}({tc['args']}) -> {result}")
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    return {"response": "Sorry, I couldn't complete that. Please call the clinic directly."}


def route_after_classify(state: AriaState) -> str:
    return "tool_agent" if state.get("intent") == "booking" else "rag"


# ─────────────────────────────────────────────
# Build Graph
# ─────────────────────────────────────────────
graph_builder = StateGraph(AriaState)
graph_builder.add_node("classifier", classify_node)
graph_builder.add_node("rag", rag_node)
graph_builder.add_node("tool_agent", tool_agent_node)
graph_builder.set_entry_point("classifier")
graph_builder.add_conditional_edges(
    "classifier",
    route_after_classify,
    {"rag": "rag", "tool_agent": "tool_agent"}
)
graph_builder.add_edge("rag", END)
graph_builder.add_edge("tool_agent", END)
aria_graph = graph_builder.compile()

# ─────────────────────────────────────────────
# Helper: run graph with session history
# ─────────────────────────────────────────────
def run_aria(user_message: str, session_id: str = "default") -> dict:
    history = get_session_history(session_id)
    # Build message list: prior history + new human message
    all_messages = list(history.messages) + [HumanMessage(content=user_message)]

    result = aria_graph.invoke({
        "messages": all_messages,
        "intent": "",
        "response": ""
    })

    # Persist to memory
    history.add_user_message(user_message)
    history.add_ai_message(result["response"])

    return result

# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────
class PatientMessage(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class AriaResponse(BaseModel):
    response: str
    intent: str
    session_id: str

# ─────────────────────────────────────────────
# Standard Endpoints
# ─────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "Aria is online",
        "clinic": "Naveen Advanced Dental Clinic",
        "version": "1.1.0"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/chat", response_model=AriaResponse)
def chat(patient_input: PatientMessage):
    result = run_aria(patient_input.message, patient_input.session_id)
    return AriaResponse(
        response=result["response"],
        intent=result["intent"],
        session_id=patient_input.session_id
    )

# ─────────────────────────────────────────────
# Bolna / OpenAI-Compatible Custom LLM Endpoint
# Bolna sends OpenAI Chat Completions format requests here.
# ─────────────────────────────────────────────
@app.post("/v1/chat/completions")
async def bolna_chat(request: Request):
    """
    Bolna AI (and Vapi) Custom LLM endpoint.
    Receives OpenAI-format chat completion requests and routes through LangGraph.
    Bolna sends the caller's speech here; Aria's LangGraph response is spoken back.
    """
    body = await request.json()

    # Extract session ID:
    # Bolna may send session_id directly, or include call metadata
    call_meta = body.get("call", {})
    session_id = (
        body.get("session_id")
        or body.get("execution_id")
        or call_meta.get("id")
        or str(uuid.uuid4())
    )

    messages = body.get("messages", [])

    # Find the last user message
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            # content can be a string or a list of content parts
            if isinstance(content, list):
                user_message = " ".join(
                    part.get("text", "") for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                )
            else:
                user_message = content
            break

    if not user_message.strip():
        return JSONResponse({
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "model": "aria",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "Sorry, I didn't catch that. Could you please repeat?"},
                "finish_reason": "stop"
            }]
        })

    print(f"[BOLNA LLM] session={session_id} | message={user_message!r}")

    # Run through LangGraph with per-call session memory
    result = run_aria(user_message, session_id)

    return JSONResponse({
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "model": "aria",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": result["response"]},
            "finish_reason": "stop"
        }]
    })

# ─────────────────────────────────────────────
# Bolna Webhook (call execution events)
# Configure in: Bolna Dashboard → Agent → Analytics tab
# ─────────────────────────────────────────────
@app.post("/bolna/webhook")
async def bolna_webhook(request: Request):
    """
    Receives Bolna AI execution webhook events.
    Bolna POSTs here on every call status change.
    Whitelist IP: 13.203.39.153
    """
    body = await request.json()
    call_status  = body.get("call_status", "unknown")
    execution_id = body.get("execution_id", "unknown")
    print(f"[BOLNA WEBHOOK] execution_id={execution_id} status={call_status}")

    if call_status in ("completed", "failed", "no-answer", "busy", "canceled",
                       "call_completed", "hangup"):
        telephony = body.get("telephony_data", {})
        log_entry = {
            "logged_at": datetime.utcnow().isoformat() + "Z",
            "call_id": execution_id,
            "event_type": "bolna_execution",
            "call_status": call_status,
            "phone_number": (
                body.get("to_number")
                or telephony.get("to_number", "unknown")
            ),
            "agent_id": body.get("agent_id", "unknown"),
            "duration_seconds": body.get("conversation_time"),
            "transcript": body.get("transcript", ""),
            "summary": body.get("summary", ""),
            "extraction_details": body.get("extraction_details", {}),
        }
        _append_call_log(log_entry)
        return {"status": "logged", "call_id": execution_id}

    return {"status": "received", "call_status": call_status}


# ─────────────────────────────────────────────
# Legacy Vapi Webhook (kept for backwards-compat)
# ─────────────────────────────────────────────
CALL_LOG_PATH = os.path.join(BASE_DIR, "..", "day13_webhook", "call_logs.json")

@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    """
    Receives Vapi webhook events (e.g. call-ended).
    Logs call metadata + transcript to call_logs.json.
    """
    body = await request.json()
    event_type = body.get("type", "unknown")
    print(f"[WEBHOOK] event={event_type}")

    if event_type in ("call-ended", "end-of-call-report"):
        call = body.get("call", body)  # some Vapi versions wrap in 'call'
        log_entry = {
            "logged_at": datetime.utcnow().isoformat() + "Z",
            "call_id": call.get("id", "unknown"),
            "event_type": event_type,
            "duration_seconds": call.get("endedAt", {}) if isinstance(call.get("endedAt"), dict) else None,
            "ended_reason": call.get("endedReason", "unknown"),
            "transcript": body.get("transcript", ""),
            "summary": body.get("summary", ""),
            "cost": body.get("cost", None),
        }
        _append_call_log(log_entry)
        return {"status": "logged", "call_id": log_entry["call_id"]}

    # Acknowledge other events without action
    return {"status": "received", "event_type": event_type}


def _append_call_log(entry: dict):
    os.makedirs(os.path.dirname(CALL_LOG_PATH), exist_ok=True)
    logs = []
    if os.path.exists(CALL_LOG_PATH):
        with open(CALL_LOG_PATH, "r", encoding="utf-8") as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
    logs.append(entry)
    with open(CALL_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f"[WEBHOOK] logged call {entry['call_id']}")


@app.get("/calls")
def get_calls():
    """Return all logged call records."""
    if not os.path.exists(CALL_LOG_PATH):
        return {"calls": [], "total": 0}
    with open(CALL_LOG_PATH, "r", encoding="utf-8") as f:
        try:
            logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
    return {"calls": logs, "total": len(logs)}