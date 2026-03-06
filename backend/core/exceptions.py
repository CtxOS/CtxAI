"""
Custom exceptions for the Ctx AI framework.

This module defines custom exception classes that are used throughout
the application to provide better error handling and debugging.
"""



class CtxAIException(Exception):
    """Base exception class for all Ctx AI framework exceptions."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AgentException(CtxAIException):
    """Exception raised for agent-related errors."""

    pass


class ModelException(CtxAIException):
    """Exception raised for model-related errors."""

    pass


class ToolException(CtxAIException):
    """Exception raised for tool execution errors."""

    pass


class ConfigurationException(CtxAIException):
    """Exception raised for configuration-related errors."""

    pass


class ValidationException(CtxAIException):
    """Exception raised for validation errors."""

    pass


class AuthenticationException(CtxAIException):
    """Exception raised for authentication failures."""

    pass


class AuthorizationException(CtxAIException):
    """Exception raised for authorization failures."""

    pass


class RateLimitException(CtxAIException):
    """Exception raised when rate limits are exceeded."""

    def __init__(
        self, message: str, retry_after: int | None = None, details: dict | None = None
    ):
        super().__init__(message, details)
        self.retry_after = retry_after


class TimeoutException(CtxAIException):
    """Exception raised when operations timeout."""

    def __init__(
        self, message: str, timeout_seconds: float | None = None, details: dict | None = None
    ):
        super().__init__(message, details)
        self.timeout_seconds = timeout_seconds
