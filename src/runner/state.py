"""Planner state definitions and helpers."""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from typing_extensions import TypedDict


class PlannerState(TypedDict, total=False):
    """State contract for the planner LangGraph workflow."""

    user_query: str
    context: str | None
    subgoals: List[str]
    tasks: List[Dict[str, Any]]
    actions: List[str]
    action_details: List[Dict[str, Any]]
    raw_goal_output: str
    headers_dict: Dict[str, Any]


class PlannerStateMaker:
    """Factory for creating planner state inputs."""

    def __init__(self) -> None:
        self._base_state: PlannerState = {
            "user_query": "",
            "context": None,
            "subgoals": [],
            "tasks": [],
            "actions": [],
            "action_details": [],
            "raw_goal_output": "",
            "headers_dict": {},
        }

    def make(self, *, user_query: str, context: str | None = None) -> PlannerState:
        """Create a fresh planner state with defaults."""
        state: PlannerState = copy.deepcopy(self._base_state)
        state["user_query"] = user_query
        state["context"] = context
        return state


__all__ = ["PlannerState", "PlannerStateMaker"]
