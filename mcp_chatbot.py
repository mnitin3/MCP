import os
import json
import asyncio
import nest_asyncio
import streamlit as st
from dotenv import load_dotenv
from typing import List
from openai import OpenAI
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.stdio import StdioServerParameters

# Setup
nest_asyncio.apply()
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
openai_base_url = os.getenv("OPENAI_BASE_URL")

class MCP_ChatBot:
    def __init__(self):
        self.session: ClientSession = None
        self.client = OpenAI(api_key=openai_api_key, base_url=openai_base_url)
        self.available_tools: List[dict] = []

    async def process_query(self, messages):
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

                    parsed_args = json.loads(tool_args)
                    result = await self.session.call_tool(tool_name, arguments=parsed_args)

                    messages.append({"role": "assistant", "tool_calls": [tool_call]})
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": result.content
                    })
            else:
                messages.append({"role": "assistant", "content": message.content})
                return messages

    async def connect_to_server(self):
        try:
            # Use dummy server params since server already running and connected manually
            server_params = StdioServerParameters(
                command=None,  # no command since not launching new process
                args=[],
                env=None
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    self.session = session
                    await session.initialize()

                    response = await session.list_tools()
                    tools = response.tools
                    self.available_tools = [{
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        }
                    } for tool in tools]
                    return tools
        except Exception as e:
            raise RuntimeError(f"Failed to connect to the MCP server: {e}")

# --- Streamlit UI ---
if "chatbot" not in st.session_state:
    st.session_state.chatbot = MCP_ChatBot()
    st.session_state.initialized = False
    st.session_state.messages = []

st.title("🤖 MCP ChatBot Interface")
st.markdown("Chat with an OpenAI-powered agent enhanced by tool use from a live MCP server.")

async def main():
    if not st.session_state.initialized:
        with st.spinner("🔌 Connecting to server..."):
            try:
                await st.session_state.chatbot.connect_to_server()
                st.session_state.initialized = True
                st.success("✅ Connected to MCP server and tools loaded.")
            except Exception as e:
                st.error(f"Connection failed: {e}")
                return

    user_input = st.chat_input("Ask your question...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.spinner("🧠 Thinking..."):
            updated_messages = await st.session_state.chatbot.process_query(st.session_state.messages)
            st.session_state.messages = updated_messages

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        elif msg["role"] == "assistant":
            st.chat_message("assistant").write(msg["content"])
        elif msg["role"] == "tool":
            st.chat_message("assistant").write(f"🛠 **Tool Response**:\n\n{msg['content']}")

# Run the async main
asyncio.run(main())
