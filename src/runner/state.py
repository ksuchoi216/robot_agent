"""Planner state definitions and helpers."""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from typing_extensions import TypedDict

from ..config.config import Config
from .text import make_group_list_text, make_object_text, make_skill_text

# from robosuite.robosuite.environments.base import make


class StateSchema(TypedDict, total=False):
    """State contract for the planner LangGraph workflow."""

    user_queries: List[str]
    inputs: Dict[str, Any]
    intent_result: Dict[str, Any]
    supervisor_result: Dict[str, Any]
    feedback_result: Dict[str, Any]
    subgoals: List[str]
    tasks: List[Dict[str, Any]]
    question_answers: List[Dict[str, Any]]


class StateMaker:
    """Factory for creating planner state inputs."""

    def __init__(self, config: Config, url: None | str = None) -> None:
        self.config = config
        if url is not None:
            self.url = url
        else:
            self.url = "http://127.0.0.1:8800"
        self._base_state: StateSchema = {
            "user_queries": [],
            "inputs": {},
            "intent_result": {},
            "supervisor_result": {},
            "feedback_result": {},
            "subgoals": [],
            "tasks": [],
            "question_answers": [],
        }

    def make_inputs(self):
        inputs = {}
        print("Making inputs for state...")
        object_text = make_object_text(self.url)
        inputs["object_text"] = object_text
        inputs["skill_text"] = make_skill_text(self.config.skills)
        print(f"url: {self.url}")
        inputs["group_list_text"] = make_group_list_text(self.url)
        return inputs

    def make(self, *, user_query: str) -> StateSchema:
        """Create a fresh state with defaults."""
        state: StateSchema = copy.deepcopy(self._base_state)
        state["user_queries"] = [user_query]
        state["inputs"] = self.make_inputs()
        return state


__all__ = ["StateSchema", "StateMaker"]
