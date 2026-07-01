import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

load_dotenv()

# 1. Connect to Groq via LangChain
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

# 2. Define the structured output we want
class InquiryClassification(BaseModel):
    intent: str = Field(description="One of: booking, pricing, emergency, general")
    urgency: str = Field(description="One of: low, medium, high")
    suggested_tone: str = Field(description="One of: reassuring, informative, urgent_action, friendly")

parser = JsonOutputParser(pydantic_object=InquiryClassification)

# 3. Build the prompt template
prompt = PromptTemplate(
    template="""You are classifying patient inquiries for a dental clinic.

Patient message: {message}

{format_instructions}
""",
    input_variables=["message"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

# 4. Chain it together with LCEL
chain = prompt | llm | parser

# 5. Test it on real-ish inputs
test_messages = [
    "My tooth has been hurting badly since last night, can someone see me today?",
    "What's the cost of a root canal at your clinic?",
    "I'd like to book a cleaning appointment for next week",
    "Do you take walk-ins?"
]

if __name__ == "__main__":
    for msg in test_messages:
        result = chain.invoke({"message": msg})
        print(f"Message: {msg}")
        print(f"Result: {result}\n")