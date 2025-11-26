"""LangGraph-based planner graph for the MLDT pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langsmith.run_helpers import traceable

from ..common.errors import GraphExecutionError, LLMError, ParsingError
from ..common.logger import get_logger
from ..common.parser import (
    parse_action_output,
    parse_goal_output,
    parse_task_output,
)
from .state import PlannerState

logger = get_logger(__name__)


@dataclass
class NodeResult:
    raw_output: str
    items: List[str]


@dataclass
class LLMChainResources:
    prompt: PromptTemplate
    llm: Any
    parser: Any

    def run(self, inputs: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        prompt_value = self.prompt.invoke(inputs)
        try:
            raw_response = self.llm.invoke(prompt_value)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(
                "LLM invocation failed.", details={"inputs": inputs}
            ) from exc

        parsed_output = self.parser.invoke(raw_response) if self.parser else raw_response
        headers = _extract_headers(raw_response, self.llm)
        return _coerce_text(parsed_output), headers


def create_llm(
    model_name: str,
    *,
    temperature: float | None = 0.0,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    model_name_str = getattr(model_name, "value", str(model_name))
    kwargs: Dict[str, Any] = {
        "model": model_name_str,
        "include_response_headers": True,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    llm = ChatOpenAI(**kwargs)
    setattr(llm, "_registered_model_name", model_name_str)
    return llm


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    content = getattr(value, "content", None)
    if isinstance(content, str):
        return content
    return str(value)


def _build_llm_chain(llm: Any, prompt_text: str) -> LLMChainResources:
    prompt = PromptTemplate.from_template(prompt_text)
    parser = StrOutputParser()
    return LLMChainResources(prompt=prompt, llm=llm, parser=parser)


def _resolve_llm_model_name(llm: Any) -> str:
    for attr in ("_registered_model_name", "model_name", "model"):
        value = getattr(llm, attr, None)
        if isinstance(value, str) and value:
            return value
    kwargs = getattr(llm, "kwargs", None)
    if isinstance(kwargs, dict):
        value = kwargs.get("model")
        if isinstance(value, str) and value:
            return value
    return "unknown"


def _extract_headers(message: Any, llm: Any) -> Dict[str, Any]:
    metadata = getattr(message, "response_metadata", None) or {}
    headers = metadata.get("headers") if isinstance(metadata, dict) else None
    token_usage = metadata.get("token_usage") if isinstance(metadata, dict) else None

    if isinstance(headers, dict):
        header_payload: Dict[str, Any] = dict(headers)
    elif headers is None:
        header_payload = {}
    else:
        header_payload = {"raw": headers}

    return {
        "model_name": _resolve_llm_model_name(llm),
        "headers": header_payload,
        "token_usage": token_usage or {},
    }


def _store_headers(
    state: Dict[str, Any],
    headers: Dict[str, Any],
    state_headers_dict_key="headers_dict",
) -> None:
    headers_dict = state.get(state_headers_dict_key)
    if headers_dict is None:
        headers_dict = {}
    model_name = headers.get("model_name") or "unknown"
    headers_dict[model_name] = headers
    state[state_headers_dict_key] = headers_dict


def _execute_with_retries(
    name: str,
    operation: Callable[[], Tuple[NodeResult, Dict[str, Any]]],
    max_retries: int,
) -> Tuple[NodeResult, Dict[str, Any]]:
    attempts = max_retries + 1
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            result, headers = operation()
            logger.info("%s succeeded on attempt %s", name, attempt)
            return result, headers
        except (ParsingError, LLMError) as exc:
            last_error = exc
            logger.warning(
                "%s failed on attempt %s/%s: %s", name, attempt, attempts, exc
            )

    raise GraphExecutionError(
        f"{name} failed after {attempts} attempts.",
        details={"node": name, "error": str(last_error) if last_error else ""},
    )


def make_goal_node(
    goal_chain: LLMChainResources,
    goal_regex: str,
    max_retries: int,
) -> Callable[[PlannerState], PlannerState]:
    @traceable(name="planner.goal", tags=["planner", "goal"])
    def goal_node(state: PlannerState) -> PlannerState:
        def _run_goal() -> Tuple[NodeResult, Dict[str, Any]]:
            raw_text, headers = goal_chain.run({"user_query": state["user_query"]})
            items = parse_goal_output(raw_text, goal_regex)
            return NodeResult(raw_output=raw_text, items=items), headers

        result, headers = _execute_with_retries(
            "GoalNode", _run_goal, max_retries=max_retries
        )
        state["subgoals"] = result.items
        state["raw_goal_output"] = result.raw_output
        _store_headers(state, headers)
        return state

    return goal_node


def make_task_node(
    task_chain: LLMChainResources,
    task_regex: str,
    max_retries: int,
) -> Callable[[PlannerState], PlannerState]:
    @traceable(name="planner.task", tags=["planner", "task"])
    def task_node(state: PlannerState) -> PlannerState:
        subgoals = state.get("subgoals", []) or []
        context_value = state.get("context") or "N/A"
        task_results: List[Dict[str, Any]] = []

        for subgoal in subgoals:
            def _run_task(subgoal: str = subgoal) -> Tuple[NodeResult, Dict[str, Any]]:
                raw_text, headers = task_chain.run(
                    {"subgoal": subgoal, "context": context_value}
                )
                items = parse_task_output(raw_text, task_regex)
                return NodeResult(raw_output=raw_text, items=items), headers

            result, headers = _execute_with_retries(
                "TaskNode", _run_task, max_retries=max_retries
            )
            task_results.append(
                {
                    "subgoal": subgoal,
                    "subtasks": result.items,
                    "raw_output": result.raw_output,
                }
            )
            _store_headers(state, headers)

        state["tasks"] = task_results
        return state

    return task_node


def make_action_node(
    action_chain: LLMChainResources,
    action_regex: str,
    max_retries: int,
) -> Callable[[PlannerState], PlannerState]:
    @traceable(name="planner.action", tags=["planner", "action"])
    def action_node(state: PlannerState) -> PlannerState:
        tasks = state.get("tasks", []) or []
        action_details: List[Dict[str, Any]] = []
        merged_actions: List[str] = []

        for task in tasks:
            for subtask in task.get("subtasks", []):
                def _run_action(
                    subtask: str = subtask,
                ) -> Tuple[NodeResult, Dict[str, Any]]:
                    raw_text, headers = action_chain.run({"subtask": subtask})
                    items = parse_action_output(raw_text, action_regex)
                    return NodeResult(raw_output=raw_text, items=items), headers

                result, headers = _execute_with_retries(
                    "ActionNode", _run_action, max_retries=max_retries
                )
                action_details.append(
                    {
                        "subtask": subtask,
                        "actions": result.items,
                        "raw_output": result.raw_output,
                    }
                )
                merged_actions.extend(result.items)
                _store_headers(state, headers)

        state["action_details"] = action_details
        state["actions"] = merged_actions
        return state

    return action_node


def create_planner_graph(
    *,
    llm: Any,
    goal_prompt: str,
    task_prompt: str,
    action_prompt: str,
    goal_regex: str,
    task_regex: str,
    action_regex: str,
    max_retries: int,
    thread_id: str = "planner",
    save_graph_png: bool = False,
) -> Tuple[Any, Dict[str, Any]]:
    goal_chain = _build_llm_chain(llm, goal_prompt)
    task_chain = _build_llm_chain(llm, task_prompt)
    action_chain = _build_llm_chain(llm, action_prompt)

    workflow = StateGraph(state_schema=PlannerState)
    workflow.add_node("goal_planner", make_goal_node(goal_chain, goal_regex, max_retries))
    workflow.add_node("task_planner", make_task_node(task_chain, task_regex, max_retries))
    workflow.add_node(
        "action_planner", make_action_node(action_chain, action_regex, max_retries)
    )

    workflow.add_edge(START, "goal_planner")
    workflow.add_edge("goal_planner", "task_planner")
    workflow.add_edge("task_planner", "action_planner")
    workflow.add_edge("action_planner", END)

    graph = workflow.compile(checkpointer=None)

    if save_graph_png:
        try:
            from langchain_core.runnables.graph_png import PngDrawer

            drawer = PngDrawer()
            drawer.draw(graph.get_graph(), "./planner_graph.png")
            logger.info("Saved planner_graph.png")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to save planner graph PNG: %s", exc)

    config = {"configurable": {"thread_id": thread_id}}
    return graph, config


__all__ = [
    "NodeResult",
    "PlannerState",
    "LLMChainResources",
    "create_llm",
    "create_planner_graph",
    "make_goal_node",
    "make_task_node",
    "make_action_node",
]
