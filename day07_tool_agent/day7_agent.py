import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage, SystemMessage
from langchain_groq import ChatGroq

load_dotenv()

# 1. Define tools
@tool
def check_appointment_availability(date: str) -> str:
    """Check available appointment slots for a given date (format: YYYY-MM-DD)."""
    mock_slots = {
        "2026-07-05": ["10:00 AM", "2:00 PM", "4:30 PM"],
        "2026-07-06": ["9:30 AM", "11:00 AM"],
    }
    slots = mock_slots.get(date, ["No slots found for this date, please try another date"])
    return f"Available slots for {date}: {', '.join(slots)}"

@tool
def book_appointment(name: str, date: str, time: str) -> str:
    """Book an appointment for a patient. Requires name, date (YYYY-MM-DD), and time."""
    return f"Appointment confirmed for {name} on {date} at {time}. A confirmation will be sent shortly."

tools = [check_appointment_availability, book_appointment]

# 2. LLM with tools bound
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

llm_with_tools = llm.bind_tools(tools)

# 3. Agent loop — keeps running until model stops calling tools
def run_agent(user_input: str, max_iterations: int = 5):
    messages = [
        SystemMessage(content="""You are Priya, a friendly dental clinic assistant.
When you get tool results, relay them directly and clearly to the patient.
Never call another tool after booking is confirmed — just confirm it to the patient.
Keep responses short and natural."""),
        {"role": "user", "content": user_input}
    ]

    for _ in range(max_iterations):
        ai_response = llm_with_tools.invoke(messages)
        messages.append(ai_response)

        # Model responded with text — we're done
        if not ai_response.tool_calls:
            return ai_response.content

        # Model wants to call tools — execute them all
        for tool_call in ai_response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            selected_tool = {t.name: t for t in tools}[tool_name]
            tool_result = selected_tool.invoke(tool_args)

            print(f"[DEBUG] Called {tool_name}({tool_args}) -> {tool_result}")

            messages.append(
                ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
            )

    return "Sorry, I couldn't complete that request. Please call the clinic directly."

# 4. Test
if __name__ == "__main__":
    test_inputs = [
        "What slots are available on 2026-07-05?",
        "Book an appointment for Rakesh Kumar on 2026-07-06 at 11:00 AM",
        "What services do you offer?"
    ]

    for msg in test_inputs:
        print(f"\nPatient: {msg}")
        response = run_agent(msg)
        print(f"Priya: {response}")