from agent_framework import WorkflowBuilder, WorkflowContext, executor
from typing_extensions import Never
from .agent import flight_agent, chart_agent
from ..schemas import FlightPriceInfo


@executor(id="flight_price_executor")
async def get_flight_info(query: str, ctx: WorkflowContext[str]) -> None:
    """Step 1: Query flight prices and return structured data"""
    # Get structured flight info
    result = await flight_agent.run(query, response_format=FlightPriceInfo)

    if result.value:
        # Send the structured JSON directly to next executor
        await ctx.send_message(result.value.model_dump_json())
    else:
        await ctx.send_message("Failed to get flight information")


@executor(id="chart_executor")
async def create_chart(flight_data: str, ctx: WorkflowContext[Never, str]) -> None:
    """Step 2: Generate chart/table from flight data"""
    # Run chart agent and collect full response
    full_text = ""
    async for update in chart_agent.run_stream(flight_data):
        if update.text:
            full_text += update.text

    # Yield complete output
    await ctx.yield_output(full_text)


# Build the workflow
def build_flight_chart_workflow():
    """Build a workflow that queries flight prices and creates a chart"""
    workflow = (
        WorkflowBuilder()
        .add_edge(get_flight_info, create_chart)
        .set_start_executor(get_flight_info)
        .build()
    )
    return workflow


# Create the workflow instance
flight_chart_workflow = build_flight_chart_workflow()
