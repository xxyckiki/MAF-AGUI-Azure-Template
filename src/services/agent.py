from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework_ag_ui import AgentFrameworkAgent
from azure.identity import AzureCliCredential
from .tools import get_flight_price, chart_mcp_tool, run_flight_chart_workflow

# Create the chat client
chat_client = AzureOpenAIChatClient(credential=AzureCliCredential())

# Flight Price Agent - 查询机票价格
flight_agent = chat_client.create_agent(
    instructions="You are a flight price assistant. Help users check flight ticket prices between different locations.",
    name="FlightPriceAgent",
    tools=[get_flight_price],
)

# Chart Agent - 生成图表
chart_agent = chat_client.create_agent(
    instructions="""You are a chart generation assistant. 
When you receive flight price information in JSON format:
1. Parse the JSON data (departure, destination, price, airline, flight_class)
2. You MUST call the chart tool to generate a table/chart with this data
3. After getting the chart URL from the tool, provide a complete response that includes:
   - A friendly summary of the flight information
   - The chart/table URL from the tool

Example response format:
"您好！查询到的票价信息：北京到东京，价格350 USD，航空公司Air China，经济舱。
我已为您生成了表格，请查看：[URL from tool]"

Remember: Always call the chart tool, don't skip it!""",
    name="ChartGeneratorAgent",
    tools=[chart_mcp_tool],
)

# CopilotKit Agent - 用于前端 AG-UI 连接
copilot_base_agent = ChatAgent(
    name="flight_chart_assistant",
    instructions="""你是一个专业的机票助手。

当用户询问机票价格时：
- 使用 query_flight_and_generate_chart 工具查询价格并生成图表
- 这个工具会自动查询价格并生成可视化图表

始终用中文友好地回复用户。如果用户只是打招呼，先问他们需要查询什么航线的机票。""",
    chat_client=chat_client,
    tools=[run_flight_chart_workflow],
)

# Wrap with AgentFrameworkAgent for AG-UI protocol
copilot_agent = AgentFrameworkAgent(
    agent=copilot_base_agent,
    name="FlightChartCopilot",
    description="机票价格查询与图表生成助手",
)

# 保持向后兼容
agent = flight_agent
