"""
Unit tests for tools module.

Test naming convention: test_<function_name>_<scenario>
"""

import pytest
from src.services.tools import get_flight_price
from src.exceptions import ToolError


class TestGetFlightPrice:
    """Tests for get_flight_price function."""

    def test_get_flight_price_success(self):
        """
        Test successful flight price query.

        This is the "happy path" - normal expected behavior.
        """
        # Arrange
        departure = "Beijing"
        destination = "Tokyo"

        # Act
        result = get_flight_price(departure, destination)

        # Assert
        assert result["departure"] == "Beijing"
        assert result["destination"] == "Tokyo"
        assert result["price"] == 350
        assert result["currency"] == "USD"
        assert "airline" in result
        assert "flight_class" in result

    def test_get_flight_price_strips_whitespace(self):
        """Test that input whitespace is stripped."""
        result = get_flight_price("  Beijing  ", "  Tokyo  ")

        assert result["departure"] == "Beijing"
        assert result["destination"] == "Tokyo"

    def test_get_flight_price_empty_departure_raises_error(self):
        """
        Test that empty departure raises ToolError.

        Use pytest.raises() to test expected exceptions.
        """
        with pytest.raises(ToolError) as exc_info:
            get_flight_price("", "Tokyo")

        assert "Departure" in str(exc_info.value)

    def test_get_flight_price_empty_destination_raises_error(self):
        """Test that empty destination raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            get_flight_price("Beijing", "")

        assert "Destination" in str(exc_info.value)

    def test_get_flight_price_whitespace_only_raises_error(self):
        """Test that whitespace-only input raises ToolError."""
        with pytest.raises(ToolError):
            get_flight_price("   ", "Tokyo")

    @pytest.mark.parametrize(
        "departure,destination",
        [
            ("New York", "London"),
            ("Shanghai", "Singapore"),
            ("Paris", "Berlin"),
        ],
    )
    def test_get_flight_price_various_routes(self, departure, destination):
        """
        Test multiple routes using parametrize.

        @pytest.mark.parametrize runs the same test with different inputs.
        This is useful for testing multiple cases without duplicate code.
        """
        result = get_flight_price(departure, destination)

        assert result["departure"] == departure
        assert result["destination"] == destination
        assert isinstance(result["price"], (int, float))
