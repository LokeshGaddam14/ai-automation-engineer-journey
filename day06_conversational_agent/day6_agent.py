import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

# 1. LLM
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

# 2. Conversation memory store
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# 3. Load existing ChromaDB vectorstore from Day 5
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Note: The folder we verified earlier was just 'chroma_db' in the parent directory, not inside 'day05_rag_chromadb'
CHROMA_PATH = os.path.join(BASE_DIR, "..", "chroma_db")

vectorstore = Chroma(
    persist_directory=CHROMA_PATH,
    embedding_function=embeddings
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

# 4. Query rewriter — turns vague follow-ups into standalone questions
rewrite_prompt = ChatPromptTemplate.from_messages([
    ("system", """Given the conversation history and the latest user question, rewrite the question 
into a standalone question that includes all necessary context. 
If the question is already standalone, return it unchanged.
Only output the rewritten question, nothing else."""),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

query_rewriter = rewrite_prompt | llm | StrOutputParser()

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def get_context(input_dict):
    standalone_question = query_rewriter.invoke({
        "input": input_dict["input"],
        "history": input_dict.get("history", [])
    })
    print(f"[DEBUG] Rewritten query: {standalone_question}")  # ADD THIS
    docs = retriever.invoke(standalone_question)
    print(f"[DEBUG] Retrieved {len(docs)} docs")  # ADD THIS
    for d in docs:
        chunk_preview = d.page_content[:80].encode('ascii', 'ignore').decode('ascii')
        print(f"[DEBUG] Chunk: {chunk_preview}...")  # ADD THIS
    return format_docs(docs)

# 5. Main conversational RAG prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are Priya, a friendly dental clinic assistant. Answer using ONLY the context below.
If the answer isn't in the context, say you don't have that information and suggest calling the clinic.
Keep answers short and natural, like a real conversation.

Context:
{context}"""),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

# 6. Chain: inject context -> prompt -> llm -> parse
chain = (
    RunnablePassthrough.assign(context=get_context)
    | prompt
    | llm
    | StrOutputParser()
)

# 7. Wrap with message history
conversational_chain = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)

# 8. Test — multi-turn conversation
if __name__ == "__main__":
    config = {"configurable": {"session_id": "patient_001"}}

    conversation = [
        "Do you do root canals?",
        "How much does that cost?",
        "Are you open right now on a Sunday?",
        "What was the first thing I asked you?"
    ]

    for msg in conversation:
        response = conversational_chain.invoke({"input": msg}, config=config)
        safe_response = response.encode('ascii', 'ignore').decode('ascii')
        print(f"Patient: {msg}")
        print(f"Priya: {safe_response}\n")