"""Centralized error definitions for the MLDT-based planner."""

from __future__ import annotations

from typing import Any, Mapping


class BaseServiceError(Exception):
    """Base exception that provides structured metadata for logging and APIs."""

    default_code = "UNKNOWN"
    default_status = 500
    default_domain = "core"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status: int | None = None,
        domain: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code or self.default_code
        self.status = status or self.default_status
        self.domain = domain or self.default_domain
        self.details = dict(details) if details else {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error_code": self.code,
            "error_message": self.message,
            "status": self.status,
            "domain": self.domain,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class ConfigError(BaseServiceError):
    """Raised when configuration files are missing or invalid."""

    default_code = "CONFIG_ERROR"


class PromptLoadError(BaseServiceError):
    """Raised when prompt templates cannot be loaded."""

    default_code = "PROMPT_LOAD_ERROR"


class ParsingError(BaseServiceError):
    """Raised when parser cannot extract structured data."""

    default_code = "PARSING_ERROR"
    default_status = 422


class LLMError(BaseServiceError):
    """Raised when LLM calls fail or responses are unusable."""

    default_code = "LLM_ERROR"
    default_status = 502


class GraphExecutionError(BaseServiceError):
    """Raised when the planner graph cannot complete execution."""

    default_code = "GRAPH_EXECUTION_ERROR"
    default_status = 500


__all__ = (
    "BaseServiceError",
    "ConfigError",
    "PromptLoadError",
    "ParsingError",
    "LLMError",
    "GraphExecutionError",
)
