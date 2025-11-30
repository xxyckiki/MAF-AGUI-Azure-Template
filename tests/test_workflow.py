"""
Unit tests for workflow module.

Note: Workflow tests are async, so we use pytest-asyncio.
"""

from src.services.workflow import flight_chart_workflow


class TestFlightChartWorkflow:
    """Tests for flight_chart_workflow."""

    def test_workflow_is_built(self):
        """Test that workflow is properly constructed."""
        assert flight_chart_workflow is not None

    # Note: Full workflow tests require mocking the agents
    # which would call external APIs (Azure OpenAI).
    #
    # For now, we just verify the workflow structure exists.
    # In a real project, you would:
    # 1. Mock the agents using pytest-mock or unittest.mock
    # 2. Test the workflow execution with mocked responses
    #
    # Example with mocking (not implemented here):
    #
    # @pytest.mark.asyncio
    # async def test_workflow_execution(self, mocker):
    #     # Mock the flight_agent
    #     mock_result = MagicMock()
    #     mock_result.value = FlightPriceInfo(...)
    #     mocker.patch.object(flight_agent, 'run', return_value=mock_result)
    #
    #     # Run workflow
    #     result = await flight_chart_workflow.run("Beijing to Tokyo")
    #
    #     # Assert
    #     assert "Tokyo" in result
