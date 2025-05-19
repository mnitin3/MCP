import os
from dotenv import load_dotenv
import asyncio
import nest_asyncio
from typing import List
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

nest_asyncio.apply()
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
openai_base_url = os.getenv("OPENAI_BASE_URL")

class MCP_ChatBot:

    def __init__(self):
        self.session: ClientSession = None
        self.client = OpenAI(api_key=openai_api_key, base_url=openai_base_url)
        self.available_tools: List[dict] = []

    async def process_query(self, query):
        messages = [{'role': 'user', 'content': query}]
        tools = self.available_tools

        while True:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.0,
                max_tokens=2000
            )

            message = response.choices[0].message

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    tool_id = tool_call.id

                    print(f"Calling tool {tool_name} with args {tool_args}")
                    # tool_args is a JSON string — parse it before using
                    import json
                    parsed_args = json.loads(tool_args)

                    result = await self.session.call_tool(tool_name, arguments=parsed_args)

                    messages.append({"role": "assistant", "tool_calls": [tool_call]})
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": result.content
                    })

            else:
                print(message.content)
                break

    async def chat_loop(self):
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                await self.process_query(query)
                print("\n")
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def connect_to_server_and_run(self):
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "research_server.py"],
            env=None,
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                await session.initialize()

                response = await session.list_tools()
                tools = response.tools
                print("\nConnected to server with tools:", [tool.name for tool in tools])

                self.available_tools = [{
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                } for tool in tools]

                await self.chat_loop()

async def main():
    chatbot = MCP_ChatBot()
    await chatbot.connect_to_server_and_run()

if __name__ == "__main__":
    asyncio.run(main())
