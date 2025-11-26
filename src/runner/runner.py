"""Planner runner wiring the LangGraph Goal -> Task -> Action pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from langsmith.run_helpers import traceable

from ..common.logger import get_logger
from ..common.utils import (
    AppConfig,
    load_config,
    load_prompt_from_dir,
    make_run_output_dir,
    resolve_path,
    save_json,
)
from .graph import create_llm, create_planner_graph
from .state import PlannerState, PlannerStateMaker

logger = get_logger(__name__)


class PlannerRunner:
    """High-level runner that initializes configuration, LLM, and LangGraph nodes."""

    def __init__(
        self,
        config_path: str | Path | None = None,
        llm: Any | None = None,
        state_maker: PlannerStateMaker | None = None,
        *,
        thread_id: str = "planner",
        save_graph_png: bool = False,
    ) -> None:
        self.project_root = Path(__file__).resolve().parents[2]
        self.config: AppConfig = load_config(config_path)

        self.prompt_dir = resolve_path(self.project_root, self.config.paths.prompt_dir)
        self.output_root = resolve_path(self.project_root, self.config.paths.output_dir)
        self.state_maker = state_maker or PlannerStateMaker()

        self.llm = llm or create_llm(
            model_name=self.config.llm.model_name,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
        )

        goal_prompt = load_prompt_from_dir(self.prompt_dir, "planning/goal_prompt.md")
        task_prompt = load_prompt_from_dir(self.prompt_dir, "planning/task_prompt.md")
        action_prompt = load_prompt_from_dir(
            self.prompt_dir, "planning/action_prompt.md"
        )

        self.graph, self.graph_config = create_planner_graph(
            llm=self.llm,
            goal_prompt=goal_prompt,
            task_prompt=task_prompt,
            action_prompt=action_prompt,
            max_retries=self.config.retry.max_retries,
            thread_id=thread_id,
            save_graph_png=save_graph_png,
        )

    @traceable(name="planner.run", tags=["planner", "graph"])
    def run(self, user_query: str, *, context: str | None = None) -> Dict[str, Any]:
        """Execute the Goal -> Task -> Action graph for a single user query."""
        logger.info("Running planner for user query: %s", user_query)

        initial_state: PlannerState = self.state_maker.make(
            user_query=user_query, context=context
        )
        final_state = self.graph.invoke(initial_state, self.graph_config)

        subgoals = final_state.get("subgoals", []) or []
        task_results = final_state.get("tasks", []) or []
        action_details = final_state.get("action_details", []) or []
        merged_actions = final_state.get("actions", []) or []

        run_dir = make_run_output_dir(self.output_root)
        self._persist_outputs(
            run_dir=run_dir,
            user_query=user_query,
            context=context,
            subgoals=subgoals,
            raw_goal_output=final_state.get("raw_goal_output", ""),
            task_results=task_results,
            action_details=action_details,
            merged_actions=merged_actions,
        )

        return {
            "user_query": user_query,
            "context": context,
            "subgoals": subgoals,
            "tasks": task_results,
            "actions": merged_actions,
            "run_dir": str(run_dir),
            "headers": final_state.get("headers_dict", {}),
        }

    def _persist_outputs(
        self,
        *,
        run_dir: Path,
        user_query: str,
        context: str | None,
        subgoals: List[str],
        raw_goal_output: str,
        task_results: List[Dict[str, Any]],
        action_details: List[Dict[str, Any]],
        merged_actions: List[str],
    ) -> None:
        goal_payload = {
            "user_query": user_query,
            "subgoals": subgoals,
            "raw_output": raw_goal_output,
        }
        task_payload = {
            "context": context,
            "tasks": task_results,
        }
        action_payload = {
            "actions": merged_actions,
            "details": action_details,
        }

        save_json(run_dir / "goal.json", goal_payload)
        save_json(run_dir / "task.json", task_payload)
        save_json(run_dir / "action.json", action_payload)
        logger.info("Saved outputs to %s", run_dir)


__all__ = ["PlannerRunner"]
