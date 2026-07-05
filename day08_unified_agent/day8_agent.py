import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.chat_history import InMemoryChatMessageHistory, BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from pydantic import BaseModel, Field

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

# --- CLASSIFIER ---
class InquiryClassification(BaseModel):
    intent: str = Field(description="One of: booking, pricing, emergency, general")
    urgency: str = Field(description="One of: low, medium, high")

classifier_parser = JsonOutputParser(pydantic_object=InquiryClassification)

classifier_prompt = ChatPromptTemplate.from_messages([
    ("system", """Classify the patient's message for a dental clinic.
{format_instructions}"""),
    ("human", "{message}")
]).partial(format_instructions=classifier_parser.get_format_instructions())

classifier_chain = classifier_prompt | llm | classifier_parser

# --- RAG ---
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAQ_PATH = os.path.join(BASE_DIR, "..", "day05_rag_chromadb", "clinic_faq.txt")

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Load and chunk the FAQ
loader = TextLoader(FAQ_PATH)
documents = loader.load()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
chunks = text_splitter.split_documents(documents)

# Build vectorstore fresh in memory (no persist — Day 8 is self-contained)
vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

print(f"[RAG] Loaded {len(chunks)} chunks into vectorstore")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are Priya, a friendly dental clinic assistant.
Answer using ONLY the context below. If the answer isn't in the context, 
say you don't have that information and suggest calling the clinic.
Keep answers short and natural.

Context:
{context}"""),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

rag_chain = (
    RunnablePassthrough.assign(context=lambda x: format_docs(retriever.invoke(x["input"])))
    | rag_prompt
    | llm
    | StrOutputParser()
)

# --- TOOLS ---
@tool
def check_appointment_availability(date: str) -> str:
    """Check available appointment slots for a given date (format: YYYY-MM-DD)."""
    mock_slots = {
        "2026-07-05": ["10:00 AM", "2:00 PM", "4:30 PM"],
        "2026-07-06": ["9:30 AM", "11:00 AM"],
        "2026-07-07": ["10:30 AM", "3:00 PM"],
    }
    slots = mock_slots.get(date, ["No slots available for this date, please try another"])
    return f"Available slots for {date}: {', '.join(slots)}"

@tool
def book_appointment(name: str, date: str, time: str) -> str:
    """Book a dental appointment. Requires patient name, date (YYYY-MM-DD), and time."""
    return f"Appointment confirmed for {name} on {date} at {time}. A confirmation will be sent shortly."

tools = [check_appointment_availability, book_appointment]
llm_with_tools = llm.bind_tools(tools)

def run_tool_agent(user_input: str, history: list, max_iterations: int = 5):
    messages = [
        SystemMessage(content="""You are Priya, a friendly dental clinic assistant.
Help patients check availability and book appointments.
When you get tool results, relay them directly and clearly.
Never call another tool after booking is confirmed."""),
        *history,
        {"role": "user", "content": user_input}
    ]

    for _ in range(max_iterations):
        ai_response = llm_with_tools.invoke(messages)
        messages.append(ai_response)

        if not ai_response.tool_calls:
            return ai_response.content

        for tool_call in ai_response.tool_calls:
            selected_tool = {t.name: t for t in tools}[tool_call["name"]]
            tool_result = selected_tool.invoke(tool_call["args"])
            print(f"[TOOL] {tool_call['name']}({tool_call['args']}) -> {tool_result}")
            messages.append(
                ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
            )

    return "Sorry, I couldn't complete that. Please call the clinic directly."

    # --- MEMORY ---
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# --- UNIFIED ROUTER ---
def priya(user_input: str, session_id: str = "default"):
    history = get_session_history(session_id)
    history_messages = history.messages

    # Step 1: Classify intent
    classification = classifier_chain.invoke({"message": user_input})
    intent = classification["intent"]
    urgency = classification["urgency"]
    print(f"[CLASSIFIER] intent={intent}, urgency={urgency}")

    # Step 2: Route based on intent
    if intent == "booking":
        response = run_tool_agent(user_input, history_messages)
    else:
        # pricing, general, emergency all go to RAG
        response = rag_chain.invoke({
            "input": user_input,
            "history": history_messages
        })

    # Step 3: Store this turn in memory
    history.add_user_message(user_input)
    history.add_ai_message(response)

    return response

# --- TEST ---
if __name__ == "__main__":
    test_conversation = [
        ("How much does a root canal cost?", "patient_001"),
        ("Are you open on Sundays?", "patient_001"),
        ("What slots are available on 2026-07-07?", "patient_001"),
        ("Book one for Lokesh at 10:30 AM on 2026-07-07", "patient_001"),
        ("What was the first thing I asked you?", "patient_001"),
    ]

    for msg, session in test_conversation:
        print(f"\nPatient: {msg}")
        response = priya(msg, session)
        print(f"Priya: {response}")

        