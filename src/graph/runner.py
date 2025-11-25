"""Planner runner wiring Goal -> Task -> Action nodes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ..common.logger import get_logger
from ..common.utils import (
    AppConfig,
    load_config,
    load_prompt_from_dir,
    make_run_output_dir,
    resolve_path,
    save_json,
)
from ..graph.graph import ActionNode, GoalNode, LLMClient, TaskNode, NodeResult

logger = get_logger(__name__)


class PlannerRunner:
    """High-level runner that initializes configuration, LLM, and MLDT nodes."""

    def __init__(
        self,
        config_path: str | Path | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.project_root = Path(__file__).resolve().parents[2]
        self.config: AppConfig = load_config(config_path)

        self.prompt_dir = resolve_path(self.project_root, self.config.paths.prompt_dir)
        self.output_root = resolve_path(self.project_root, self.config.paths.output_dir)

        self.llm = llm_client or LLMClient(
            model_name=self.config.llm.model_name,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
        )

        goal_prompt = load_prompt_from_dir(self.prompt_dir, "goal/goal_prompt.md")
        task_prompt = load_prompt_from_dir(self.prompt_dir, "task/task_prompt.md")
        action_prompt = load_prompt_from_dir(self.prompt_dir, "action/action_prompt.md")

        retries = self.config.retry.max_retries
        self.goal_node = GoalNode(
            llm=self.llm,
            prompt_text=goal_prompt,
            goal_regex=self.config.parsing.goal_regex,
            max_retries=retries,
        )
        self.task_node = TaskNode(
            llm=self.llm,
            prompt_text=task_prompt,
            task_regex=self.config.parsing.task_regex,
            max_retries=retries,
        )
        self.action_node = ActionNode(
            llm=self.llm,
            prompt_text=action_prompt,
            action_regex=self.config.parsing.action_regex,
            max_retries=retries,
        )

    def run(self, user_query: str, *, context: str | None = None) -> Dict[str, Any]:
        """Execute the Goal -> Task -> Action graph for a single user query."""
        logger.info("Running planner for user query: %s", user_query)
        goal_result = self.goal_node.run(user_query)
        task_results: List[Dict[str, Any]] = []
        action_results: List[Dict[str, Any]] = []

        for subgoal in goal_result.items:
            task_result = self.task_node.run(subgoal, context=context)
            task_results.append(
                {
                    "subgoal": subgoal,
                    "subtasks": task_result.items,
                    "raw_output": task_result.raw_output,
                }
            )

            for subtask in task_result.items:
                action_result = self.action_node.run(subtask)
                action_results.append(
                    {
                        "subtask": subtask,
                        "actions": action_result.items,
                        "raw_output": action_result.raw_output,
                    }
                )

        merged_actions = [
            action for result in action_results for action in result["actions"]
        ]

        run_dir = make_run_output_dir(self.output_root)
        self._persist_outputs(
            run_dir=run_dir,
            user_query=user_query,
            context=context,
            goal_result=goal_result,
            task_results=task_results,
            action_results=action_results,
            merged_actions=merged_actions,
        )

        return {
            "user_query": user_query,
            "context": context,
            "subgoals": goal_result.items,
            "tasks": task_results,
            "actions": merged_actions,
            "run_dir": str(run_dir),
        }

    def _persist_outputs(
        self,
        *,
        run_dir: Path,
        user_query: str,
        context: str | None,
        goal_result: NodeResult,
        task_results: List[Dict[str, Any]],
        action_results: List[Dict[str, Any]],
        merged_actions: List[str],
    ) -> None:
        goal_payload = {
            "user_query": user_query,
            "subgoals": goal_result.items,
            "raw_output": goal_result.raw_output,
        }
        task_payload = {
            "context": context,
            "tasks": task_results,
        }
        action_payload = {
            "actions": merged_actions,
            "details": action_results,
        }

        save_json(run_dir / "goal.json", goal_payload)
        save_json(run_dir / "task.json", task_payload)
        save_json(run_dir / "action.json", action_payload)
        logger.info("Saved outputs to %s", run_dir)


__all__ = ["PlannerRunner"]
