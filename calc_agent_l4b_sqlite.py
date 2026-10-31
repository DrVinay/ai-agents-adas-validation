from openai import OpenAI
import json
import sqlite3
from datetime import datetime

client = OpenAI()


# =================================================
# DATABASE SETUP
# =================================================

DB_FILE = "agent_memory.db"


def init_database():
    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# =================================================
# SAVE MEMORY
# =================================================

def save_memory(role, content):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO memory (role, content, created_at)
        VALUES (?, ?, ?)
        """,
        (
            role,
            content,
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()


# =================================================
# LOAD MEMORY
# =================================================

def load_memory(limit=20):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role, content
        FROM memory
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cursor.fetchall()

    conn.close()

    # Because SQL returned newest first,
    # reverse it back into conversation order
    rows.reverse()

    conversation = []

    for role, content in rows:

        conversation.append(
            {
                "role": role,
                "content": content
            }
        )

    return conversation


# =================================================
# TOOL 1: CALCULATOR
# =================================================

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


# =================================================
# TOOL 2: CURRENT TIME
# =================================================

def get_current_time():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# =================================================
# TOOL 3: VEHICLE STATUS
# =================================================

def get_vehicle_status():

    return {
        "battery_percent": 82,
        "speed_kmph": 0,
        "ignition": "ON",
        "adas_system": "READY"
    }


# =================================================
# TOOL DEFINITIONS
# =================================================

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
        "description": "Get current vehicle status including battery percentage, speed, ignition and ADAS state.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]


# =================================================
# AGENT INSTRUCTIONS
# =================================================

agent_instruction = """
You are a Level 4 AI agent with persistent memory.

You can:
1. Understand the user's goal.
2. Use available tools.
3. Use multiple tools when required.
4. Use previous conversation history.
5. Remember information from earlier sessions.
6. Use previ 
7. Return concise final answers.

Do not invent tool results.
"""


# =================================================
# INITIALIZE DATABASE
# =================================================

init_database()

print("Persistent memory database ready.")


# =================================================
# MAIN CONVERSATION LOOP
# =================================================

while True:

    user_input = input("\nYou: ")


    if user_input.lower() in [
        "exit",
        "quit"
    ]:

        print("Agent stopped.")
        break


    # ---------------------------------------------
    # SAVE USER MESSAGE TO DATABASE
    # ---------------------------------------------

    save_memory(
        "user",
        user_input
    )


    # ---------------------------------------------
    # LOAD MEMORY FROM DATABASE
    # ---------------------------------------------

    conversation = load_memory(
        limit=20
    )


    # ---------------------------------------------
    # FIRST LLM CALL
    # ---------------------------------------------

    response = client.responses.create(

        model="gpt-5.6",

        instructions=agent_instruction,

        input=conversation,

        tools=tools
    )


    # =============================================
    # AGENT TOOL LOOP
    # =============================================

    while True:

        tool_outputs = []


        for item in response.output:


            if item.type == "function_call":

                print(
                    "\nAgent decided to use:",
                    item.name
                )


                args = json.loads(
                    item.arguments
                )


                print(
                    "Arguments:",
                    args
                )


                # ---------------------------------
                # TOOL ROUTER
                # ---------------------------------

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


                print(
                    "Tool result:",
                    result
                )


                tool_outputs.append(

                    {
                        "type": "function_call_output",

                        "call_id": item.call_id,

                        "output": json.dumps(result)
                    }

                )


        # =========================================
        # FINAL ANSWER
        # =========================================

        if not tool_outputs:

            final_answer = response.output_text


            print(
                "\nAgent:",
                final_answer
            )


            # -------------------------------------
            # SAVE AGENT RESPONSE TO DATABASE
            # -------------------------------------

            save_memory(
                "assistant",
                final_answer
            )


            break

        # =========================================
        # CONTINUE TOOL LOOP
        # =========================================

        response = client.responses.create(

            model="gpt-5.6",

            instructions=agent_instruction,

            previous_response_id=response.id,

            input=tool_outputs,

            tools=tools
        )