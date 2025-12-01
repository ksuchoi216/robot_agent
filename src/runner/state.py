"""Planner state definitions and helpers."""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from typing_extensions import TypedDict

from ..config.config import Config
from .text import make_object_text, make_skill_text


class PlannerState(TypedDict, total=False):
    """State contract for the planner LangGraph workflow."""

    user_query: str
    inputs: Dict[str, Any]
    subgoals: List[str]
    tasks: List[Dict[str, Any]]

    # actions: List[str]
    # action_details: List[Dict[str, Any]]


class PlannerStateMaker:
    """Factory for creating planner state inputs."""

    def __init__(self, config: Config, url: None | str = None) -> None:
        self.config = config
        if url is not None:
            self.url = url
        else:
            self.url = "http://127.0.0.1:8800"
        self._base_state: PlannerState = {
            "user_query": "",
            "inputs": {},
            "subgoals": [],
            "tasks": [],
            # "actions": [],
            # "action_details": [],
        }

    def make_inputs(self):
        inputs = {}
        object_text_dict = make_object_text(self.url)
        inputs["object_text_dict"] = object_text_dict
        inputs["skill_text"] = make_skill_text(self.config.skills)
        return inputs

    def make(self, *, user_query: str) -> PlannerState:
        """Create a fresh planner state with defaults."""
        state: PlannerState = copy.deepcopy(self._base_state)
        state["user_query"] = user_query
        state["inputs"] = self.make_inputs()
        return state


__all__ = ["PlannerState", "PlannerStateMaker"]
