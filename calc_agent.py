from openai import OpenAI
import json

client = OpenAI()


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


tools = [
    {
        "type": "function",
        "name": "calculator",
        "description": "Perform basic arithmetic calculations.",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"]
                }
            },
            "required": ["a", "b", "operation"]
        }
    }
]


user_input = input("You: ")

response = client.responses.create(
    model="gpt-5.6",
    input=user_input,
    tools=tools
)

tool_outputs = []

for item in response.output:
    if item.type == "function_call":
        print("\nAgent decided to use:", item.name)

        args = json.loads(item.arguments)

        print("Arguments:", args)

        result = calculator(
            args["a"],
            args["b"],
            args["operation"]
        )

        print("Tool result:", result)

        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": str(result)
            }
        )


if tool_outputs:
    final_response = client.responses.create(
        model="gpt-5.6",
        previous_response_id=response.id,
        input=tool_outputs,
        tools=tools
    )

    print("\nAgent:", final_response.output_text)

else:
    print("\nAgent:", response.output_text)