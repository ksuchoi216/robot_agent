"""Centralized error definitions for the oneit interview AI module."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional


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


__all__ = ("BaseServiceError",)
