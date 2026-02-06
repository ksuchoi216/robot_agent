"""
Minimal stub for the `numba` module.

`robosuite` uses `numba.jit` for optional acceleration, but the full dependency
is heavy and not required for correctness in this project. This shim makes the
import succeed and turns JIT decorators into no-ops.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def jit(*args: Any, **kwargs: Any):  # noqa: D401
    """Return a decorator that leaves the function unchanged."""

    def _decorator(func: F) -> F:
        return func

    # Supports both `@jit` and `@jit(...)` usage.
    if args and callable(args[0]) and len(args) == 1 and not kwargs:
        return _decorator(args[0])
    return _decorator


__all__ = ["jit"]

