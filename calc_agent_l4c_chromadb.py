from openai import OpenAI
import chromadb
import json
import uuid
from datetime import datetime

client = OpenAI()


# =================================================
# CHROMADB SETUP
# =================================================

chroma_client = chromadb.PersistentClient(
    path="./chroma_memory"
)

memory_collection = chroma_client.get_or_create_collection(
    name="agent_memory"
)


# =================================================
# CREATE EMBEDDING
# =================================================

def create_embedding(text):

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )

    return response.data[0].embedding


# =================================================
# SAVE SEMANTIC MEMORY
# =================================================

def save_memory(role, content):

    embedding = create_embedding(content)

    memory_collection.add(

        ids=[
            str(uuid.uuid4())
        ],

        documents=[
            content
        ],

        embeddings=[
            embedding
        ],

        metadatas=[
            {
                "role": role,
                "created_at": datetime.now().isoformat()
            }
        ]
    )


# =================================================
# RETRIEVE RELEVANT MEMORIES
# =================================================

def retrieve_memories(query, limit=5):

    query_embedding = create_embedding(query)

    results = memory_collection.query(

        query_embeddings=[
            query_embedding
        ],

        n_results=limit
    )


    memories = []


    if results["documents"]:

        for document in results["documents"][0]:

            memories.append(document)


    return memories


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
You are a Level 4 AI agent with semantic persistent memory.

You can:
1. Understand the user's goal.
2. Use retrieved memories from previous sessions. (RAG concept)
3. If the answer is already clearly available in retrieved memory,
   answer directly from memory and do not call tools unnecessarily.
4. Use tools only when current or new information is required.
5. Use multiple tools when required.
6. Connect semantically similar memories to the current question.
7. Do not invent memories or tool results.
8. Return concise final answers.
"""


print("Semantic memory database ready.")


# =================================================
# MAIN LOOP
# =================================================

while True:

    user_input = input("\nYou: ")


    if user_input.lower() in [
        "exit",
        "quit"
    ]:

        print("Agent stopped.")
        break


    # =================================================
    # SEARCH SEMANTIC MEMORY
    # =================================================

    memories = retrieve_memories(
        user_input,
        limit=5
    )


    print("\nRelevant memories:")

    for memory in memories:
        print("-", memory)


    # =================================================
    # BUILD CONTEXT
    # =================================================

    memory_text = "\n".join(
        memories
    )


    prompt = f"""
Relevant memories from previous conversations:

{memory_text}

Current user request:

{user_input}
"""


    # =================================================
    # FIRST LLM CALL
    # =================================================

    response = client.responses.create(

        model="gpt-5.6",

        instructions=agent_instruction,

        input=prompt,

        tools=tools
    )


    # =================================================
    # AGENT TOOL LOOP
    # =================================================

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


        # =================================================
        # FINAL ANSWER
        # =================================================

        if not tool_outputs:

            final_answer = response.output_text


            print(
                "\nAgent:",
                final_answer
            )


            # ---------------------------------------------
            # SAVE USER QUESTION
            # ---------------------------------------------

            save_memory(
                "user",
                user_input
            )


            # ---------------------------------------------
            # SAVE AGENT ANSWER
            # ---------------------------------------------

            save_memory(
                "assistant",
                final_answer
            )


            break


        # =================================================
        # CONTINUE TOOL LOOP
        # =================================================

        response = client.responses.create(

            model="gpt-5.6",

            instructions=agent_instruction,

            previous_response_id=response.id,

            input=tool_outputs,

            tools=tools
        )