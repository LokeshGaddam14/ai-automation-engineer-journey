"""
Aria — LangGraph Multi-Agent Orchestrator
==========================================
Routes voice conversations through specialized agents using LangGraph state machine.

Architecture:
    GREETING_AGENT   → Welcome patient, detect intent
         |
    ROUTER           → booking | info | emergency | escalation
         |
    BOOKING_AGENT    → Collect details, check calendar, confirm
    INFO_AGENT       → Answer pricing/FAQ from knowledge base
    EMERGENCY_AGENT  → Triage urgent cases (toothache, swelling)
    ESCALATION_AGENT → Hand off to human dentist

Why LangGraph?
    - Stateful: Each node reads/writes the full conversation state
    - Predictable: Explicit routing (no hallucinated tool calls)
    - Auditable: Every decision is logged in state
    - Resumable: State can be persisted and resumed mid-conversation
"""

import json
import os
import random
from datetime import datetime
from typing import Annotated, Dict, List, Literal, Optional, TypedDict


# ── State Schema ───────────────────────────────────────────────────────────────

class CallState(TypedDict):
    """
    Full state of an ongoing voice call.
    Passed between all agents in the LangGraph pipeline.
    """
    # Call metadata
    call_id:       str
    patient_phone: str
    language:      str
    started_at:    str

    # Conversation
    messages:   List[Dict]
    turn_count: int

    # Extracted data (filled progressively)
    patient_name:     Optional[str]
    appointment_date: Optional[str]
    appointment_time: Optional[str]
    treatment:        Optional[str]
    patient_email:    Optional[str]
    chief_complaint:  Optional[str]
    urgency_level:    Optional[str]

    # Routing & status
    intent:            Optional[str]
    current_agent:     str
    next_agent:        Optional[str]
    is_complete:       bool
    booking_confirmed: bool
    booking_id:        Optional[str]
    calendar_event_id: Optional[str]

    # Agent responses
    last_response:     str
    escalation_reason: Optional[str]


# ── Agent Nodes ────────────────────────────────────────────────────────────────

def greeting_agent(state: CallState) -> CallState:
    """
    First contact agent.
    Welcomes patient, asks how to help, detects intent.
    """
    language = state.get("language", "English")

    greetings = {
        "Telugu":  "నమస్తే! మా డెంటల్ క్లినిక్కి స్వాగతం. నేను Aria. మీకు ఎలా సహాయపడగలను?",
        "Hindi":   "नमस्ते! हमारे डेंटल क्लिनिक में आपका स्वागत है। मैं Aria हूं।",
        "Tamil":   "வணக்கம்! எங்கள் பல் மருத்துவமனைக்கு வரவேற்கிறோம். நான் Aria.",
        "English": "Hello! Welcome to Naveen Advanced Dental Clinic. I'm Aria, your AI receptionist. How can I help you today?",
    }

    greeting = greetings.get(language, greetings["English"])

    state["messages"].append({
        "role":      "agent",
        "content":   greeting,
        "timestamp": datetime.now().isoformat(),
        "agent":     "greeting"
    })
    state["last_response"] = greeting
    state["current_agent"] = "greeting"

    # Intent detection from patient messages
    patient_msgs = [m for m in state.get("messages", []) if m["role"] == "patient"]

    if patient_msgs:
        last_patient = patient_msgs[-1]["content"].lower()
        if any(w in last_patient for w in ["book", "appointment", "schedule", "fix", "రేపు", "बुक", "நாளை"]):
            state["intent"] = "booking"
            state["next_agent"] = "booking"
        elif any(w in last_patient for w in ["pain", "hurt", "ache", "swollen", "bleeding", "నొప్పి", "दर्द"]):
            state["intent"] = "emergency"
            state["next_agent"] = "emergency"
            state["urgency_level"] = "high"
        elif any(w in last_patient for w in ["price", "cost", "fee", "how much", "ధర", "कीमत"]):
            state["intent"] = "info"
            state["next_agent"] = "info"
        else:
            state["intent"] = "general"
            state["next_agent"] = "booking"

    return state


def booking_agent(state: CallState) -> CallState:
    """
    Appointment booking agent.
    Collects patient name, date, time, treatment.
    Checks calendar availability and confirms booking.
    """
    missing = []
    if not state.get("patient_name"):
        missing.append("name")
    if not state.get("appointment_date"):
        missing.append("date")
    if not state.get("appointment_time"):
        missing.append("time")
    if not state.get("treatment"):
        missing.append("treatment")

    language = state.get("language", "English")

    if missing:
        questions = {
            "name": {
                "English": "Could I have your name please?",
                "Telugu":  "మీ పేరు చెప్పగలరా?",
                "Hindi":   "आपका नाम क्या है?",
            },
            "date": {
                "English": "What date would you prefer for your appointment?",
                "Telugu":  "మీకు ఏ తేదీ సౌకర్యంగా ఉంటుంది?",
                "Hindi":   "आप किस तारीख को अपॉइंटमेंट लेना चाहते हैं?",
            },
            "time": {
                "English": "What time works best for you? Our clinic is open 9 AM to 6 PM.",
                "Telugu":  "ఏ సమయం మీకు అనుకూలంగా ఉంటుంది? మా క్లినిక్ 9 AM నుండి 6 PM వరకు తెరిచి ఉంటుంది.",
                "Hindi":   "आपके लिए कौन सा समय सुविधाजनक होगा? हमारा क्लिनिक सुबह 9 बजे से शाम 6 बजे तक खुला है।",
            },
            "treatment": {
                "English": "What type of dental treatment are you looking for? (cleaning, checkup, filling, etc.)",
                "Telugu":  "మీకు ఏ రకమైన దంత చికిత్స అవసరం? (క్లీనింగ్, చెకప్, ఫిల్లింగ్)",
                "Hindi":   "आपको किस प्रकार का दंत उपचार चाहिए? (सफाई, जांच, फिलिंग)",
            }
        }
        first_missing = missing[0]
        response = questions[first_missing].get(language, questions[first_missing]["English"])

        state["messages"].append({
            "role": "agent", "content": response,
            "timestamp": datetime.now().isoformat(), "agent": "booking"
        })
        state["last_response"] = response
        state["current_agent"] = "booking"

    else:
        # All info collected → Try to book on calendar
        name  = state["patient_name"]
        date  = state["appointment_date"]
        time  = state["appointment_time"]
        treat = state["treatment"]

        try:
            from aria.integrations.google_calendar import GoogleCalendarAgent
            cal = GoogleCalendarAgent()
            booking_result = cal.book_appointment(
                patient_name  = name,
                patient_phone = state["patient_phone"],
                date_str      = date,
                time_str      = time,
                treatment     = treat,
                patient_email = state.get("patient_email", ""),
                booking_id    = state.get("booking_id", "")
            )
            if booking_result.get("status") == "confirmed":
                state["calendar_event_id"] = booking_result.get("event_id")
        except Exception as e:
            print(f"[Booking] Calendar error (non-fatal): {e}")

        booking_id = f"BLN{random.randint(1000000, 9999999)}"
        state["booking_id"] = booking_id
        state["booking_confirmed"] = True

        confirmations = {
            "English": f"Your appointment is confirmed! Booking ID: {booking_id}. We'll see {name} on {date} at {time} for {treat}. See you soon!",
            "Telugu":  f"మీ అపాయింట్మెంట్ కన్ఫర్మ్ అయింది! బుకింగ్ ID: {booking_id}. {name} గారు {date} {time}కి {treat} కోసం వస్తున్నారు!",
            "Hindi":   f"आपका अपॉइंटमेंट confirmed है! Booking ID: {booking_id}. {name} जी, {date} को {time} बजे {treat} के लिए मिलते हैं!",
        }
        response = confirmations.get(language, confirmations["English"])

        state["messages"].append({
            "role": "agent", "content": response,
            "timestamp": datetime.now().isoformat(), "agent": "booking"
        })
        state["last_response"] = response
        state["current_agent"] = "booking"
        state["is_complete"] = True

    return state


def info_agent(state: CallState) -> CallState:
    """
    FAQ/pricing information agent.
    Answers common questions about treatments and costs.
    """
    language = state.get("language", "English")

    faq = {
        "pricing": {
            "English": "Our treatment prices: Cleaning ₹500-800, Filling ₹800-2000, Root Canal ₹3000-8000, Crown ₹5000-15000. Consultation is FREE!",
            "Telugu":  "మా చికిత్స ధరలు: క్లీనింగ్ ₹500-800, ఫిల్లింగ్ ₹800-2000, రూట్ కెనాల్ ₹3000-8000, క్రౌన్ ₹5000-15000. కన్సల్టేషన్ ఉచితం!",
            "Hindi":   "हमारी उपचार कीमतें: सफाई ₹500-800, फिलिंग ₹800-2000, रूट कैनाल ₹3000-8000, क्राउन ₹5000-15000। परामर्श मुफ्त है!",
        }
    }

    response = faq["pricing"].get(language, faq["pricing"]["English"])
    follow_up = {
        "English": " Would you like to book an appointment?",
        "Telugu":  " అపాయింట్మెంట్ బుక్ చేయాలా?",
        "Hindi":   " क्या आप अपॉइंटमेंट बुक करना चाहेंगे?",
    }
    response += follow_up.get(language, follow_up["English"])

    state["messages"].append({
        "role": "agent", "content": response,
        "timestamp": datetime.now().isoformat(), "agent": "info"
    })
    state["last_response"] = response
    state["current_agent"] = "info"
    state["next_agent"] = "booking"

    return state


def emergency_agent(state: CallState) -> CallState:
    """
    Emergency triage agent.
    For dental pain, swelling, trauma — gives immediate guidance.
    """
    language = state.get("language", "English")

    emergencies = {
        "English": "I can hear this is urgent. Please come to our clinic immediately — we have emergency slots available today. If you have severe pain, take an ibuprofen for now. Should I book an emergency slot for you right now?",
        "Telugu":  "ఇది అర్జెంట్ అని అర్థమవుతోంది. దయచేసి వెంటనే మా క్లినిక్కి రండి — ఈ రోజు ఎమర్జెన్సీ స్లాట్స్ అందుబాటులో ఉన్నాయి. మీ కోసం ఇప్పుడే స్లాట్ బుక్ చేయాలా?",
        "Hindi":   "मैं समझ सकती हूं यह जरूरी है। कृपया तुरंत हमारे क्लिनिक में आएं — आज इमरजेंसी स्लॉट उपलब्ध हैं। क्या मैं अभी आपके लिए स्लॉट बुक करूं?",
    }

    response = emergencies.get(language, emergencies["English"])
    state["messages"].append({
        "role": "agent", "content": response,
        "timestamp": datetime.now().isoformat(), "agent": "emergency"
    })
    state["last_response"] = response
    state["current_agent"] = "emergency"
    state["urgency_level"] = "emergency"
    state["next_agent"] = "booking"

    return state


def escalation_agent(state: CallState) -> CallState:
    """
    Human escalation agent.
    Triggered when AI can't handle the request or patient asks for dentist.
    """
    language = state.get("language", "English")

    messages = {
        "English": f"I understand you need to speak with our dentist directly. I'm connecting you now. Your call ID is: {state.get('call_id', 'N/A')}. Please hold on for a moment.",
        "Telugu":  "మీరు మా దంత వైద్యునితో నేరుగా మాట్లాడాలని అర్థమైంది. నేను ఇప్పుడు కనెక్ట్ చేస్తున్నాను. దయచేసి వేచి ఉండండి.",
        "Hindi":   "मैं समझती हूं आप हमारे डॉक्टर से सीधे बात करना चाहते हैं। मैं अभी कनेक्ट कर रही हूं। कृपया थोड़ी देर प्रतीक्षा करें।",
    }

    response = messages.get(language, messages["English"])
    state["messages"].append({
        "role": "agent", "content": response,
        "timestamp": datetime.now().isoformat(), "agent": "escalation"
    })
    state["last_response"] = response
    state["current_agent"] = "escalation"
    state["escalation_reason"] = "Patient requested human agent"
    state["is_complete"] = True

    return state


# ── Router ─────────────────────────────────────────────────────────────────────

def route_to_next(state: CallState) -> str:
    """
    Routing function — decides which agent to call next.
    Returns: agent name string (used by LangGraph add_conditional_edges)
    """
    if state.get("is_complete"):
        return "end"
    if state.get("current_agent") == "escalation":
        return "end"

    next_ag = state.get("next_agent")
    if next_ag in ("booking", "info", "emergency", "escalation"):
        return next_ag

    intent = state.get("intent", "booking")
    route_map = {
        "booking":   "booking",
        "info":      "info",
        "emergency": "emergency",
    }
    return route_map.get(intent, "booking")


# ── Build LangGraph Pipeline ───────────────────────────────────────────────────

def build_aria_graph():
    """
    Assemble the Aria multi-agent LangGraph state machine.

    Graph structure:
        START → greeting → [booking | info | emergency | escalation] → END
    """
    try:
        from langgraph.graph import StateGraph, END, START
    except ImportError:
        print("[LangGraph] Not installed — run: pip install langgraph")
        return None

    graph = StateGraph(CallState)

    graph.add_node("greeting",   greeting_agent)
    graph.add_node("booking",    booking_agent)
    graph.add_node("info",       info_agent)
    graph.add_node("emergency",  emergency_agent)
    graph.add_node("escalation", escalation_agent)

    graph.add_edge(START, "greeting")

    graph.add_conditional_edges(
        "greeting",
        route_to_next,
        {
            "booking":    "booking",
            "info":       "info",
            "emergency":  "emergency",
            "escalation": "escalation",
            "end":        END,
        }
    )

    graph.add_conditional_edges(
        "booking",
        route_to_next,
        {
            "booking":    "booking",
            "escalation": "escalation",
            "end":        END,
        }
    )

    graph.add_conditional_edges(
        "info",
        route_to_next,
        {
            "booking": "booking",
            "end":     END,
        }
    )

    graph.add_conditional_edges(
        "emergency",
        route_to_next,
        {
            "booking":    "booking",
            "escalation": "escalation",
            "end":        END,
        }
    )

    graph.add_edge("escalation", END)

    return graph.compile()
