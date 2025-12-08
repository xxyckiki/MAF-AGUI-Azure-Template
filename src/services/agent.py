import os
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework_ag_ui import AgentFrameworkAgent
from azure.identity import (
    ManagedIdentityCredential,
    AzureCliCredential,
    ChainedTokenCredential,
)
from .tools import get_flight_price, chart_mcp_tool, run_flight_chart_workflow
from ..db import CosmosChatMessageStore


def get_credential():
    """Get credential based on environment."""
    # Cloud: use Managed Identity first, Local: use Azure CLI
    # ChainedTokenCredential tries each credential in order until one succeeds
    return ChainedTokenCredential(
        ManagedIdentityCredential(),  # Cloud
        AzureCliCredential(),  # Local
    )


# Create the chat client
chat_client = AzureOpenAIChatClient(
    credential=get_credential(),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-5-nano"),
)

# Flight Price Agent - Query flight prices
flight_agent = chat_client.create_agent(
    instructions="You are a flight price assistant. Help users check flight ticket prices between different locations.",
    name="FlightPriceAgent",
    tools=[get_flight_price],
)

# Chart Agent - Generate charts
chart_agent = chat_client.create_agent(
    instructions="""You are a chart generation assistant.
When you receive flight price information in JSON format:
1. Parse the JSON data (departure, destination, price, airline, flight_class)
2. You MUST call the chart tool to generate a table/chart with this data
3. After getting the chart URL from the tool, provide a complete response that includes:
   - A friendly summary of the flight information
   - The chart/table URL from the tool

Example response format:
"Here's the flight information: Beijing to Tokyo, Price: 350 USD, Airline: Air China, Class: Economy.
I've generated a table for you, please check: [URL from tool]"

Remember: Always call the chart tool, don't skip it!""",
    name="ChartGeneratorAgent",
    tools=[chart_mcp_tool],
)

# CopilotKit Agent - For frontend AG-UI connection
copilot_base_agent = ChatAgent(
    name="flight_chart_assistant",
    instructions="""You are a professional flight assistant.

When a user asks about flight prices:
- Use the query_flight_and_generate_chart tool to query prices and generate charts
- This tool automatically queries prices and generates visualizations

Always respond in a friendly manner. If the user just says hello, ask them which route they want to query.""",
    chat_client=chat_client,
    tools=[run_flight_chart_workflow],
    chat_message_store_factory=lambda: CosmosChatMessageStore(
        session_id=os.getenv("DEFAULT_SESSION_ID", "default_session"),
        max_messages=100,  # Keep up to 100 messages
    ),
)

# Wrap with AgentFrameworkAgent for AG-UI protocol
copilot_agent = AgentFrameworkAgent(
    agent=copilot_base_agent,
    name="FlightChartCopilot",
    description="Flight price query and chart generation assistant",
)

# Backward compatibility alias
agent = flight_agent
