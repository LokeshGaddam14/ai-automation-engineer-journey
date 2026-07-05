import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

from langgraph.graph.message import add_messages

# State definition — shared across all nodes
class PriyaState(TypedDict):
    messages: Annotated[list, add_messages]  # full conversation history
    intent: str                               # set by classifier node
    response: str                             # final response to patient

from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field

# --- RAG Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAQ_PATH = os.path.join(BASE_DIR, "..", "day05_rag_chromadb", "clinic_faq.txt")

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
loader = TextLoader(FAQ_PATH)
documents = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
chunks = splitter.split_documents(documents)
vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

# --- Tools ---
@tool
def check_appointment_availability(date: str) -> str:
    """Check available appointment slots for a given date (format: YYYY-MM-DD)."""
    mock_slots = {
        "2026-07-05": ["10:00 AM", "2:00 PM", "4:30 PM"],
        "2026-07-06": ["9:30 AM", "11:00 AM"],
        "2026-07-07": ["10:30 AM", "3:00 PM"],
    }
    slots = mock_slots.get(date, ["No slots available for this date"])
    return f"Available slots for {date}: {', '.join(slots)}"

@tool
def book_appointment(name: str, date: str, time: str) -> str:
    """Book a dental appointment. Requires patient name, date (YYYY-MM-DD), and time."""
    return f"Appointment confirmed for {name} on {date} at {time}. Confirmation will be sent shortly."

tools = [check_appointment_availability, book_appointment]
llm_with_tools = llm.bind_tools(tools)
tools_map = {t.name: t for t in tools}

# --- NODE 1: Classifier ---
def classify_node(state: PriyaState) -> PriyaState:
    last_message = state["messages"][-1].content
    prompt = f"""Classify this dental clinic patient message into one of: booking, pricing, emergency, general.
Reply with just the single word intent.
Message: {last_message}"""
    result = llm.invoke(prompt)
    intent = result.content.strip().lower()
    # Normalize
    if "book" in intent:
        intent = "booking"
    elif "pric" in intent or "cost" in intent:
        intent = "pricing"
    elif "emerg" in intent:
        intent = "emergency"
    else:
        intent = "general"
    print(f"[NODE: classifier] intent={intent}")
    return {"intent": intent}

# --- NODE 2: RAG ---
def rag_node(state: PriyaState) -> PriyaState:
    last_message = state["messages"][-1].content
    docs = retriever.invoke(last_message)
    context = "\n\n".join(d.page_content for d in docs)
    prompt = f"""You are Priya, a friendly dental clinic assistant.
Answer using ONLY this context. If answer isn't here, suggest calling the clinic.
Keep it short and natural.

Context:
{context}

Patient: {last_message}"""
    result = llm.invoke(prompt)
    print(f"[NODE: rag] responding with RAG answer")
    return {
        "messages": [AIMessage(content=result.content)],
        "response": result.content
    }

# --- NODE 3: Tool Agent ---
def tool_agent_node(state: PriyaState) -> PriyaState:
    messages = [
        SystemMessage(content="""You are Priya, a dental clinic assistant.
Help patients check availability and book appointments.
Relay tool results clearly. Never call another tool after booking."""),
        *state["messages"]
    ]
    for _ in range(5):
        ai_response = llm_with_tools.invoke(messages)
        messages.append(ai_response)
        if not ai_response.tool_calls:
            print(f"[NODE: tool_agent] done, returning response")
            return {
                "messages": [AIMessage(content=ai_response.content)],
                "response": ai_response.content
            }
        for tool_call in ai_response.tool_calls:
            result = tools_map[tool_call["name"]].invoke(tool_call["args"])
            print(f"[TOOL] {tool_call['name']}({tool_call['args']}) -> {result}")
            messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    return {"response": "Sorry, couldn't complete that. Please call the clinic."}

# --- ROUTER: decides which node to go to after classifier ---
def route_after_classify(state: PriyaState) -> str:
    intent = state.get("intent", "general")
    if intent == "booking":
        return "tool_agent"
    return "rag"

# --- BUILD GRAPH ---
graph_builder = StateGraph(PriyaState)

# Add nodes
graph_builder.add_node("classifier", classify_node)
graph_builder.add_node("rag", rag_node)
graph_builder.add_node("tool_agent", tool_agent_node)

# Entry point
graph_builder.set_entry_point("classifier")

# Conditional routing after classifier
graph_builder.add_conditional_edges(
    "classifier",
    route_after_classify,
    {
        "rag": "rag",
        "tool_agent": "tool_agent"
    }
)

# Both rag and tool_agent end the graph
graph_builder.add_edge("rag", END)
graph_builder.add_edge("tool_agent", END)

# Compile
priya_graph = graph_builder.compile()
print("Graph compiled OK")

# --- TEST ---
if __name__ == "__main__":
    test_inputs = [
        "How much does a root canal cost?",
        "Are you open on Sundays?",
        "What slots are available on 2026-07-07?",
        "Book an appointment for Lokesh on 2026-07-07 at 10:30 AM",
    ]

    for msg in test_inputs:
        print(f"\nPatient: {msg}")
        result = priya_graph.invoke({
            "messages": [HumanMessage(content=msg)],
            "intent": "",
            "response": ""
        })
        print(f"Priya: {result['response']}")
