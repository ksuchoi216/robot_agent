from __future__ import annotations

from importlib import import_module
from typing import Any, Callable


def _load_graph_modules(graph_name: str) -> tuple[Any, Any]:
    try:
        state_module = import_module(f".{graph_name}.state", package=__name__)
        graph_module = import_module(f".{graph_name}.graph", package=__name__)
    except ModuleNotFoundError as exc:
        raise ValueError(f"Unknown graph name: {graph_name!r}") from exc

    return state_module, graph_module


def get_make_state(graph_name: str) -> Callable[..., Any]:
    """Return make_state for a named graph package."""
    state_module, _ = _load_graph_modules(graph_name)

    state_func = getattr(state_module, "make_state", None)
    if not callable(state_func):
        raise ValueError(f"Graph {graph_name!r} is missing make_state().")

    return state_func


def get_graph(graph_name: str) -> Any:
    """Return compiled graph for a named graph package."""
    _, graph_module = _load_graph_modules(graph_name)

    create_graph = getattr(graph_module, "create_graph", None)
    if not callable(create_graph):
        raise ValueError(f"Graph {graph_name!r} is missing create_graph().")

    return create_graph()


__all__ = ["get_make_state", "get_graph"]
