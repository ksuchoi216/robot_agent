"""MLDT planning graph definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from ..common.errors import GraphExecutionError, LLMError, ParsingError
from ..common.logger import get_logger
from ..common.parser import (
    parse_action_output,
    parse_goal_output,
    parse_task_output,
)

logger = get_logger(__name__)


@dataclass
class NodeResult:
    raw_output: str
    items: List[str]


class LLMClient:
    """Thin wrapper around the OpenAI client to simplify dependency injection."""

    def __init__(
        self,
        model_name: str,
        temperature: float | None = 0.0,
        max_tokens: int = 2048,
        client: Optional[object] = None,
    ) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = client or self._build_client()

    def _build_client(self) -> object:
        try:
            from openai import OpenAI
        except Exception as exc:
            raise LLMError(
                "Failed to initialize OpenAI client; install and set credentials.",
                details={"model_name": self.model_name},
            ) from exc
        return OpenAI()

    def generate(self, prompt: str) -> str:
        """Generate text from the LLM."""
        if callable(self._client):
            try:
                return str(self._client(prompt))
            except Exception as exc:
                raise LLMError(
                    "Custom LLM callable failed.",
                    details={"model_name": self.model_name},
                ) from exc

        kwargs = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
        }
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature

        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise LLMError(
                f"LLM generation failed: {exc}",
                details={"model_name": self.model_name},
            ) from exc

        choices = getattr(response, "choices", None)
        if isinstance(choices, list) and choices:
            first = choices[0]
            message = getattr(first, "message", None)
            if message is not None:
                content = getattr(message, "content", None)
                if content:
                    return str(content).strip()
            if hasattr(first, "text"):
                return str(getattr(first, "text")).strip()

        raise LLMError(
            "LLM response missing content.",
            details={"model_name": self.model_name},
        )


class _BaseNode:
    """Shared retry and parsing logic for MLDT nodes."""

    def __init__(
        self,
        name: str,
        llm: LLMClient,
        prompt_text: str,
        parse_func: Callable[[str], List[str]],
        max_retries: int,
    ) -> None:
        self.name = name
        self.llm = llm
        self.prompt_text = prompt_text
        self.parse_func = parse_func
        self.max_retries = max_retries

    def _execute(self, prompt: str) -> NodeResult:
        attempts = self.max_retries + 1
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                raw_output = self.llm.generate(prompt)
                items = self.parse_func(raw_output)
                logger.info("%s succeeded on attempt %s", self.name, attempt)
                return NodeResult(raw_output=raw_output, items=items)
            except (ParsingError, LLMError) as exc:
                last_error = exc
                logger.warning(
                    "%s failed on attempt %s/%s: %s",
                    self.name,
                    attempt,
                    attempts,
                    exc,
                )
        raise GraphExecutionError(
            f"{self.name} failed after {attempts} attempts.",
            details={"node": self.name, "error": str(last_error) if last_error else ""},
        )


class GoalNode(_BaseNode):
    """Goal-level MLDT node: user query -> subgoals."""

    def __init__(
        self,
        llm: LLMClient,
        prompt_text: str,
        goal_regex: str,
        max_retries: int,
    ) -> None:
        super().__init__(
            name="GoalNode",
            llm=llm,
            prompt_text=prompt_text,
            parse_func=lambda text: parse_goal_output(text, goal_regex),
            max_retries=max_retries,
        )

    def run(self, user_query: str) -> NodeResult:
        prompt = self.prompt_text.format(user_query=user_query)
        return self._execute(prompt)


class TaskNode(_BaseNode):
    """Task-level MLDT node: subgoal -> subtasks."""

    def __init__(
        self,
        llm: LLMClient,
        prompt_text: str,
        task_regex: str,
        max_retries: int,
    ) -> None:
        super().__init__(
            name="TaskNode",
            llm=llm,
            prompt_text=prompt_text,
            parse_func=lambda text: parse_task_output(text, task_regex),
            max_retries=max_retries,
        )

    def run(self, subgoal: str, *, context: str | None = None) -> NodeResult:
        context_value = context if context else "N/A"
        prompt = self.prompt_text.format(subgoal=subgoal, context=context_value)
        return self._execute(prompt)


class ActionNode(_BaseNode):
    """Action-level MLDT node: subtask -> primitive actions."""

    def __init__(
        self,
        llm: LLMClient,
        prompt_text: str,
        action_regex: str,
        max_retries: int,
    ) -> None:
        super().__init__(
            name="ActionNode",
            llm=llm,
            prompt_text=prompt_text,
            parse_func=lambda text: parse_action_output(text, action_regex),
            max_retries=max_retries,
        )

    def run(self, subtask: str) -> NodeResult:
        prompt = self.prompt_text.format(subtask=subtask)
        return self._execute(prompt)


__all__ = ["LLMClient", "NodeResult", "GoalNode", "TaskNode", "ActionNode"]
