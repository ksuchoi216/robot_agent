"""Planner state definitions and helpers."""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from typing_extensions import TypedDict

from ..config.config import Config
from .text import make_group_list_text, make_object_text, make_skill_text

# from robosuite.robosuite.environments.base import make


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
        }

    def make_inputs(self):
        inputs = {}
        print("Making inputs for planner state...")
        object_text = make_object_text(self.url)
        inputs["object_text"] = object_text
        inputs["skill_text"] = make_skill_text(self.config.skills)
        print(f"url: {self.url}")
        inputs["group_list_text"] = make_group_list_text(self.url)
        return inputs

    def make(self, *, user_query: str) -> PlannerState:
        """Create a fresh planner state with defaults."""
        state: PlannerState = copy.deepcopy(self._base_state)
        state["user_query"] = user_query
        state["inputs"] = self.make_inputs()
        return state


__all__ = ["PlannerState", "PlannerStateMaker"]
