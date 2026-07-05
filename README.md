# 🚀 AI Automation Engineer — Build Log

A hands-on journey building production-grade AI automation skills. This repository tracks my progression through LangChain, RAG, LangGraph, and web APIs — applied directly to building **Priya**, a stateful AI assistant for a dental clinic.

---

## 📅 Progress Tracking

### Core Concepts & Fundamentals
- **Day 4** — **LangChain Fundamentals**: Structured output classification using prompt templates, Pydantic parsers, and LCEL chains.
- **Day 5** — **RAG Pipeline**: Implemented document chunking, embeddings, ChromaDB retrieval, and grounded Q&A.
- **Day 6** — **Conversational Agent**: Integrated memory with a combined classify-then-retrieve flow for seamless dialogue.
- **Day 7** — **Tool Calling Agent**: Developed an autonomous agent loop with LangChain's `@tool` decorator, enabling the LLM to execute external functions like checking availability and booking appointments.

### Productionizing & Orchestrating
- **Day 8** — **Unified Agent**: Unified intent classification, tool calling, conversational memory, and in-memory RAG loading into a single chatbot pipeline.
- **Day 9** — **LangGraph Migration**: Refactored the unified agent into a stateful, predictable LangGraph state machine.
- **Day 10** — **FastAPI Integration**: Wrapped the LangGraph agent in a FastAPI web service, exposing `/chat` and `/health` endpoints for external API integrations.

---

## 🏗️ Architecture

```mermaid
graph TD
    User([User Message]) --> Classifier[Classifier Node]
    Classifier --> Route{Route based on Intent}
    Route -- booking --> ToolAgent[Tool Agent Node]
    Route -- pricing/general/emergency --> RAG[RAG Node]
    ToolAgent --> End([Final Response])
    RAG --> End
```

---

## 🛠️ Tech Stack
- **Framework**: LangChain, LangGraph
- **API Framework**: FastAPI, Uvicorn
- **LLM**: Groq (llama-3.3-70b-versatile)
- **Vector Store**: ChromaDB (In-Memory)
- **Embeddings**: HuggingFace (`sentence-transformers/all-MiniLM-L6-v2`)
- **Language**: Python

---

## 🚀 How to Run the Project

### 1. Install dependencies
```bash
pip install fastapi uvicorn langchain langchain-groq langchain-huggingface langchain-chroma langgraph python-dotenv langchain-community langchain-text-splitters
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run the FastAPI Server (Day 10)
```bash
python -m uvicorn day10_fastapi.day10_api:app --reload --port 8000
```

### 4. Query the API
Send a POST request to the `/chat` endpoint:
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/chat" -Method POST -ContentType "application/json" -Body '{"message": "How much does a root canal cost?", "session_id": "test_001"}' -UseBasicParsing
```