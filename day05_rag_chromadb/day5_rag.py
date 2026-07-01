import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# Step 1: Load the document
loader = TextLoader("clinic_faq.txt", encoding="utf-8")
documents = loader.load()

# Step 2: Split into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50
)
chunks = text_splitter.split_documents(documents)

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

rag_prompt = PromptTemplate(
    template="""Answer the patient's question using ONLY the context below.
If the answer isn't in the context, say you don't have that information and suggest calling the clinic.

Context:
{context}

Question: {question}

Answer:""",
    input_variables=["context", "question"]
)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
    | StrOutputParser()
)

# Step 5: Test it
test_questions = [
    "How much does a root canal cost?",
    "Are you open on Sundays?",
    "Do you accept insurance?",
    "Do you offer free dental implants?"
]

for q in test_questions:
    answer = rag_chain.invoke(q)
    print(f"Q: {q}")
    print(f"A: {answer}\n")
print(f"Stored {len(chunks)} chunks in ChromaDB")
print(f"Loaded {len(documents)} document(s)")
print(f"Split into {len(chunks)} chunks")
print("\n--- First chunk preview ---")
print(chunks[0].page_content)