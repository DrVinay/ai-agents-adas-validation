from openai import OpenAI
import json
from datetime import datetime

client = OpenAI()


# -------------------------------------------------
# TOOL 1: Calculator
# -------------------------------------------------
def calculator(a, b, operation):

    if operation == "add":
        return a + b

    elif operation == "subtract":
        return a - b

    elif operation == "multiply":
        return a * b

    elif operation == "divide":
        return a / b

    else:
        raise ValueError("Unsupported operation")


# -------------------------------------------------
# TOOL 2: Current Time
# -------------------------------------------------
def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------------------
# TOOL 3: Vehicle Status
# -------------------------------------------------
def get_vehicle_status():

    # Dummy data for learning
    return {
        "battery_percent": 82,
        "speed_kmph": 0,
        "ignition": "ON",
        "adas_system": "READY"
    }


# -------------------------------------------------
# TOOL DEFINITIONS
# -------------------------------------------------
tools = [

    {
        "type": "function",
        "name": "calculator",
        "description": "Perform arithmetic calculations.",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
                "operation": {
                    "type": "string",
                    "enum": [
                        "add",
                        "subtract",
                        "multiply",
                        "divide"
                    ]
                }
            },
            "required": ["a", "b", "operation"]
        }
    },

    {
        "type": "function",
        "name": "get_current_time",
        "description": "Get the current local system time.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },

    {
        "type": "function",
        "name": "get_vehicle_status",
        "description": "Get current vehicle status including battery percentage, speed, ignition and ADAS system state.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]


# -------------------------------------------------
# MEMORY
# -------------------------------------------------
conversation = []


# -------------------------------------------------
# SYSTEM / AGENT INSTRUCTION
# -------------------------------------------------
agent_instruction = """
You are a Level 4 AI agent.

Your behavior:
1. Understand the user's goal.
2. Create a short internal plan before acting.
3. Use available tools when necessary.
4. Use multiple tools if the task requires it.
5. Remember previous conversation context.
6. Use previous results when the user refers to them later.
7. Adapt your approach if new information changes the task.
8. Return a concise final answer.

Do not invent tool results.
"""


# -------------------------------------------------
# MAIN CONVERSATION LOOP
# -------------------------------------------------
while True:

    user_input = input("\nYou: ")

    if user_input.lower() in ["exit", "quit"]:
        print("Agent stopped.")
        break


    # Store user message in memory
    conversation.append(
        {
            "role": "user",
            "content": user_input
        }
    )


    # -------------------------------------------------
    # FIRST LLM CALL
    # -------------------------------------------------
    response = client.responses.create(

        model="gpt-5.6",

        instructions=agent_instruction,

        input=conversation,

        tools=tools
    )


    # -------------------------------------------------
    # AGENT TOOL LOOP
    # -------------------------------------------------
    while True:

        tool_outputs = []


        for item in response.output:

            if item.type == "function_call":

                print("\nAgent decided to use:", item.name)

                args = json.loads(item.arguments)

                print("Arguments:", args)


                # -------------------------------------
                # TOOL ROUTER
                # -------------------------------------

                if item.name == "calculator":

                    result = calculator(
                        args["a"],
                        args["b"],
                        args["operation"]
                    )


                elif item.name == "get_current_time":

                    result = get_current_time()


                elif item.name == "get_vehicle_status":

                    result = get_vehicle_status()


                else:

                    result = "Unknown tool"


                print("Tool result:", result)


                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result)
                    }
                )


        # -------------------------------------------------
        # FINAL ANSWER
        # -------------------------------------------------
        if not tool_outputs:

            final_answer = response.output_text

            print("\nAgent:", final_answer)


            # Store assistant answer in memory
            conversation.append(
                {
                    "role": "assistant",
                    "content": final_answer
                }
            )

            break


        # -------------------------------------------------
        # CONTINUE TOOL REASONING
        # -------------------------------------------------
        response = client.responses.create(

            model="gpt-5.6",

            instructions=agent_instruction,

            previous_response_id=response.id,

            input=tool_outputs,

            tools=tools
        )