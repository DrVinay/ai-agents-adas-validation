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

    # Dummy vehicle data for learning
    return {
        "battery_percent": 82,
        "speed_kmph": 0,
        "ignition": "ON",
        "adas_system": "READY"
    }


# -------------------------------------------------
# TOOL DEFINITIONS FOR THE LLM
# -------------------------------------------------
tools = [

    {
        "type": "function",
        "name": "calculator",
        "description": "Perform arithmetic calculations.",
        "parameters": {
            "type": "object",
            "properties": {

                "a": {
                    "type": "number"
                },

                "b": {
                    "type": "number"
                },

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

            "required": [
                "a",
                "b",
                "operation"
            ]
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
# USER INPUT
# -------------------------------------------------
user_input = input("You: ")


# -------------------------------------------------
# FIRST LLM CALL
# -------------------------------------------------
response = client.responses.create(

    model="gpt-5.6",

    input=user_input,

    tools=tools
)


# -------------------------------------------------
# AGENT LOOP
# -------------------------------------------------
while True:

    tool_outputs = []

    print("\n--- Checking agent response ---")


    # Look through everything returned by the LLM
    for item in response.output:


        # Did the LLM request a tool?
        if item.type == "function_call":

            print("\nAgent decided to use:", item.name)

            args = json.loads(item.arguments)

            print("Arguments:", args)


            # -----------------------------------------
            # TOOL ROUTER
            # -----------------------------------------

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


            # Give tool result back to the LLM
            tool_outputs.append(

                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result)
                }

            )


    # -------------------------------------------------
    # NO MORE TOOL CALLS
    # -------------------------------------------------
    if not tool_outputs:

        print("\nAgent:", response.output_text)

        break


    # -------------------------------------------------
    # SEND TOOL RESULTS BACK TO LLM
    # -------------------------------------------------
    response = client.responses.create(

        model="gpt-5.6",

        previous_response_id=response.id,

        input=tool_outputs,

        tools=tools

    )