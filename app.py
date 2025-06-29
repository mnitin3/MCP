# pip install -U 'autogen-ext[mcp]' json-schema-to-pydantic>=0.2.2
# uv tool install mcp-server-fetch
# verify it in path by running uv tool update-shell
import asyncio
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console
import os
from dotenv import load_dotenv
load_dotenv()

# Load environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_base_url = os.getenv("OPENAI_BASE_URL")

if not openai_api_key or not openai_base_url:
    raise ValueError("OpenAI API key or base URL is not set. Please check your environment variables.")

async def main() -> None:
    # Setup server params for local filesystem access
    fetch_mcp_server = StdioServerParams(command="uvx", args=["mcp-server-fetch"], env=None)
    tools = await mcp_server_tools(fetch_mcp_server)

    # Setup research server params and tools
    research_mcp_server = StdioServerParams(command="uv", args=["run", "research_server.py"], env=None)
    research_tools = await mcp_server_tools(research_mcp_server)

    # Create agents for each server
    model_client = OpenAIChatCompletionClient(model="gpt-4o", api_key=openai_api_key, base_url=openai_base_url)
    agent = AssistantAgent(name="fetcher", model_client=model_client, tools=tools, reflect_on_tool_use=True)  # type: ignore
    researcher = AssistantAgent(name="researcher", model_client=model_client, tools=research_tools, reflect_on_tool_use=True)  # type: ignore

    termination = MaxMessageTermination(
        max_messages=5) | TextMentionTermination("TERMINATE")

    team = RoundRobinGroupChat([agent, researcher], termination_condition=termination)
    #  team.dump_component().model_dump()

    await Console(team.run_stream(task="Summarize the content of https://newsletter.victordibia.com/p/you-have-ai-fatigue-thats-why-you", cancellation_token=CancellationToken()))
    await Console(team.run_stream(task="Analyze the MSFT stock based on last week data.", cancellation_token=CancellationToken()))
    
if __name__ == "__main__":
    asyncio.run(main())
