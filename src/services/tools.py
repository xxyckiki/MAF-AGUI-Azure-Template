from typing import Annotated
from pydantic import Field
from agent_framework import ai_function, MCPStdioTool, WorkflowOutputEvent
from ..exceptions import ToolError


@ai_function(
    name="check_flight_price",
    description="Check flight ticket prices between two locations",
)
def get_flight_price(
    departure: Annotated[str, Field(description="The departure city or airport code")],
    destination: Annotated[
        str, Field(description="The destination city or airport code")
    ],
) -> dict:
    """Returns flight price information as a dictionary."""
    try:
        # Validate input
        if not departure or not departure.strip():
            raise ToolError("Departure location cannot be empty")
        if not destination or not destination.strip():
            raise ToolError("Destination location cannot be empty")

        return {
            "departure": departure.strip(),
            "destination": destination.strip(),
            "price": 350.0,
            "currency": "USD",
            "airline": "Air China",
            "flight_class": "Economy",
        }
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to query flight price: {e}") from e


# Chart Generator MCP Tool
chart_mcp_tool = MCPStdioTool(
    name="chart-generator-mcp",
    command="npx",
    args=["-y", "@antv/mcp-server-chart"],
)


# Workflow Tool - Wrap workflow as a callable tool
@ai_function(
    name="query_flight_and_generate_chart",
    description="Query flight prices and automatically generate a chart. Call this tool when user asks about flight prices.",
)
async def run_flight_chart_workflow(
    query: Annotated[
        str,
        Field(
            description="User's flight query request, e.g., 'flights from Beijing to Tokyo'"
        ),
    ],
) -> str:
    """Execute the flight-chart workflow and return the result."""
    from ..exceptions import WorkflowError

    try:
        # Validate input
        if not query or not query.strip():
            raise WorkflowError("Query content cannot be empty")

        # Delayed import to avoid circular dependency
        from .workflow import flight_chart_workflow

        result = ""
        async for event in flight_chart_workflow.run_stream(query):
            if isinstance(event, WorkflowOutputEvent):
                result = event.data

        if not result:
            raise WorkflowError("Workflow returned no result")

        return result
    except WorkflowError:
        raise
    except Exception as e:
        raise WorkflowError(f"Failed to execute workflow: {e}") from e
