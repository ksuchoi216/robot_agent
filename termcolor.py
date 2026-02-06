"""
Minimal fallback implementation of the `termcolor` package.

The upstream `robosuite` / `robocasa` repos use `termcolor.colored()` for nicer CLI logs.
In this workspace we avoid adding network-installed deps; this shim keeps imports working.
"""

from __future__ import annotations

from typing import Any


def colored(text: str, color: str | None = None, on_color: str | None = None, attrs: Any = None) -> str:
    # No-op colorizer. We intentionally ignore color / attrs.
    return text

