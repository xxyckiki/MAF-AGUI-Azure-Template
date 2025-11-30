"""
Unified Exception Handling Module

Provides:
- Custom exception classes
- Global exception handlers
- Structured error responses
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================================
# Error Response Model
# ============================================================================


class ErrorResponse(BaseModel):
    """Unified error response format"""

    error: str  # Error type
    message: str  # User-friendly error message
    detail: str | None = None  # Detailed info (dev environment only)


# ============================================================================
# Custom Exception Classes
# ============================================================================


class AppException(Exception):
    """Base application exception"""

    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type: str = "InternalError",
    ):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(self.message)


class AgentError(AppException):
    """Agent execution error"""

    def __init__(self, message: str = "Agent execution failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="AgentError",
        )


class WorkflowError(AppException):
    """Workflow execution error"""

    def __init__(self, message: str = "Workflow execution failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="WorkflowError",
        )


class ToolError(AppException):
    """Tool execution error"""

    def __init__(self, message: str = "Tool execution failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="ToolError",
        )


class ValidationError(AppException):
    """Request validation error"""

    def __init__(self, message: str = "Invalid request"):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type="ValidationError",
        )


class ConfigurationError(AppException):
    """Configuration error"""

    def __init__(self, message: str = "Configuration error"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="ConfigurationError",
        )


# ============================================================================
# Global Exception Handlers
# ============================================================================


def register_exception_handlers(app: FastAPI, debug: bool = False) -> None:
    """
    Register global exception handlers

    Args:
        app: FastAPI application instance
        debug: Whether to show detailed error info (should be False in production)
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        """Handle custom application exceptions"""
        logger.error(f"{exc.error_type}: {exc.message}", exc_info=True)

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.error_type,
                message=exc.message,
                detail=str(exc) if debug else None,
            ).model_dump(),
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle value errors"""
        logger.warning(f"ValueError: {exc}")

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="ValidationError",
                message="Invalid request parameters",
                detail=str(exc) if debug else None,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all uncaught exceptions"""
        logger.exception(f"Unhandled exception: {exc}")

        # Hide detailed error info in production
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="InternalError",
                message="Internal server error, please try again later",
                detail=str(exc) if debug else None,
            ).model_dump(),
        )
