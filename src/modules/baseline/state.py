"""Planner state definitions and helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from typing_extensions import TypedDict


class StateSchema(TypedDict, total=False):
    input_dict: Dict[str, Any]
    result: str


def _make_base_state() -> StateSchema:
    return {
        "input_dict": {},
        "result": "",
    }


def _make_inputs(data_dict) -> Dict[str, Any]:
    return data_dict


def make_state(data_dict) -> StateSchema:
    """Create a fresh state with defaults."""
    state = _make_base_state()
    state["input_dict"] = _make_inputs(data_dict)
    return state
