"""
Unit tests for exceptions module.
"""

import pytest
from fastapi import status
from src.exceptions import (
    AppException,
    AgentError,
    WorkflowError,
    ToolError,
    ValidationError,
    ConfigurationError,
)


class TestExceptionClasses:
    """Tests for custom exception classes."""

    def test_app_exception_default_values(self):
        """Test AppException with default values."""
        exc = AppException()

        assert exc.message == "An error occurred"
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.error_type == "InternalError"

    def test_app_exception_custom_values(self):
        """Test AppException with custom values."""
        exc = AppException(
            message="Custom error",
            status_code=400,
            error_type="CustomError",
        )

        assert exc.message == "Custom error"
        assert exc.status_code == 400
        assert exc.error_type == "CustomError"

    def test_agent_error(self):
        """Test AgentError exception."""
        exc = AgentError("Agent failed to respond")

        assert exc.message == "Agent failed to respond"
        assert exc.error_type == "AgentError"
        assert exc.status_code == 500

    def test_workflow_error(self):
        """Test WorkflowError exception."""
        exc = WorkflowError("Workflow timeout")

        assert exc.message == "Workflow timeout"
        assert exc.error_type == "WorkflowError"

    def test_tool_error(self):
        """Test ToolError exception."""
        exc = ToolError("Tool not found")

        assert exc.message == "Tool not found"
        assert exc.error_type == "ToolError"

    def test_validation_error_has_400_status(self):
        """Test ValidationError has 400 status code."""
        exc = ValidationError("Invalid input")

        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.error_type == "ValidationError"

    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        exc = ConfigurationError("Missing API key")

        assert exc.message == "Missing API key"
        assert exc.error_type == "ConfigurationError"

    def test_exception_inheritance(self):
        """Test that all exceptions inherit from AppException."""
        assert issubclass(AgentError, AppException)
        assert issubclass(WorkflowError, AppException)
        assert issubclass(ToolError, AppException)
        assert issubclass(ValidationError, AppException)
        assert issubclass(ConfigurationError, AppException)

    def test_exception_can_be_raised_and_caught(self):
        """Test exceptions can be properly raised and caught."""
        with pytest.raises(AppException):
            raise ToolError("Test error")
