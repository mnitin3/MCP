import streamlit as st
import asyncio
import nest_asyncio
from mcp_client import MCP_ChatBot  # assumes mcp_client.py is in the same folder

nest_asyncio.apply()

# Streamlit app
st.set_page_config(page_title="MCP Chatbot", layout="wide")
st.title("🤖 MCP Chatbot with Tool Calling")

# Initialize chatbot session once
@st.cache_resource
def init_chatbot():
    chatbot = MCP_ChatBot()
    asyncio.run(chatbot.connect_to_server_and_run())
    return chatbot

chatbot = init_chatbot()

# Session state to store chat messages
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input
if prompt := st.chat_input("Enter your query..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    async def handle_query():
        # Override process_query to store and return messages
        messages = [{'role': 'user', 'content': prompt}]
        tools = chatbot.available_tools
        output = ""

        while True:
            response = chatbot.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.0,
                max_tokens=2000
            )

            message = response.choices[0].message

            if message.tool_calls:
                import json
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_id = tool_call.id

                    result = await chatbot.session.call_tool(tool_name, arguments=tool_args)

                    messages.append({"role": "assistant", "tool_calls": [tool_call]})
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": result.content
                    })
            else:
                output = message.content
                messages.append({"role": "assistant", "content": output})
                return output

    response_text = asyncio.run(handle_query())

    with st.chat_message("assistant"):
        st.markdown(response_text)
    st.session_state.messages.append({"role": "assistant", "content": response_text})
