"""Planner runner wiring the LangGraph Goal -> Task -> Action pipeline."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from ..common.enums import ModelNames
from ..common.errors import GraphInitializeError
from ..common.logger import get_logger
from ..config.config import Config

# from ..prompts.planning_prompt import (
#     GOAL_NODE_PROMPT,
#     TASK_NODE_PROMPT,
#     GoalNodeParser,
#     TaskNodeParser,
#     make_goal_node_inputs,
#     make_task_node_inputs,
# )
from ..prompts import planning_prompt, process_prompt
from . import graph as graph_module
from .state import StateSchema

logger = get_logger(__name__)


class Runner:
    def __init__(
        self,
        config: Config,
        token_information_changed_callback: Callable | None = None,
    ):
        self.config = config
        self.graph: Any | None = None
        self.graph_config: Dict[str, Any] | None = None
        self.retriever = None

        self._llm_cache: Dict[Tuple[str, float, str | None, bool], Any] = {}

        if token_information_changed_callback is not None:
            self.token_information_changed_callback = token_information_changed_callback
        else:
            self.token_information_changed_callback = None

    def set_retriever(self, retriever):
        self.retriever = retriever
        self.graph = None
        self.graph_config = None

    def build_graph(self):
        raise NotImplementedError("Subclasses must implement build_graph().")

    def _get_llm(
        self,
        model_name: ModelNames | str,
        *,
        temperature: float = 0.0,
        prompt_cache_key: str | None = None,
        bind_tools: bool = False,
    ):
        if isinstance(model_name, ModelNames):
            model_enum = model_name
        else:
            try:
                # Try interpret as enum value (e.g., "gpt-4.1")
                model_enum = ModelNames(model_name)
            except ValueError:
                # Fallback to enum key (e.g., "gpt_4_1")
                model_enum = ModelNames[model_name]

        cache_key = (model_enum.value, temperature, prompt_cache_key, bind_tools)
        llm = self._llm_cache.get(cache_key)
        if llm is None:
            llm = graph_module.create_llm(
                model_name=model_enum,
                temperature=temperature,
                prompt_cache_key=prompt_cache_key,
            )
            self._llm_cache[cache_key] = llm
        return llm

    def _ensure_graph(self) -> Tuple[Any, Dict[str, Any]]:
        if self.graph is None or self.graph_config is None:
            self.graph, self.graph_config = self.build_graph()
        if self.graph is None or self.graph_config is None:
            raise GraphInitializeError(
                "Graph or graph_config is not properly initialized."
            )
        return self.graph, self.graph_config

    def invoke(self, state):
        graph, graph_config = self._ensure_graph()
        final_state = graph.invoke(state, graph_config)
        return final_state

    def batch(self, states):
        graph, graph_config = self._ensure_graph()
        final_states = graph.batch(states, graph_config)
        return final_states


class PlanRunner(Runner):
    def build_graph(self):
        goal_node = graph_module.make_normal_node(
            llm=self._get_llm(
                model_name=self.config.runner.goal_decomp_node.model_name,
                prompt_cache_key=self.config.runner.goal_decomp_node.prompt_cache_key,
            ),
            prompt_text=planning_prompt.GOAL_DECOMP_NODE_PROMPT,
            make_inputs=planning_prompt.make_goal_decomp_node_inputs,
            parser_output=planning_prompt.GoalDecompNodeParser,
            state_key="subgoals",
            state_append=False,
            node_name="GOAL_NODE",
        )
        task_node = graph_module.make_normal_node(
            llm=self._get_llm(
                model_name=self.config.runner.task_decomp_node.model_name,
                prompt_cache_key=self.config.runner.task_decomp_node.prompt_cache_key,
            ),
            prompt_text=planning_prompt.TASK_DECOMP_NODE_PROMPT,
            make_inputs=planning_prompt.make_task_decomp_node_inputs,
            parser_output=planning_prompt.TaskDecompNodeParser,
            state_key="tasks",
            state_append=False,
            node_name="TASK_NODE",
        )

        return graph_module.make_plan_graph(
            state_schema=StateSchema,
            goal_node=goal_node,
            task_node=task_node,
            thread_id="planning",
        )


class SupervisedPlanRunner(Runner):
    def build_graph(self):
        nodes = {}
        routers = {}
        nodes["user_input"] = graph_module.make_user_input_node(
            state_key="user_queries", state_append=True
        )
        nodes["intent"] = graph_module.make_normal_node(
            llm=self._get_llm(
                model_name=self.config.runner.intent_node.model_name,
                prompt_cache_key=self.config.runner.intent_node.prompt_cache_key,
            ),
            prompt_text=process_prompt.INTENT_NODE_PROMPT,
            make_inputs=process_prompt.make_intent_node_inputs,
            parser_output=process_prompt.IntentParser,
            state_key="intent_result",
            state_append=False,
            node_name="INTENT_NODE",
        )
        routers["intent"] = process_prompt.route_intent

        nodes["supervisor"] = graph_module.make_normal_node(
            llm=self._get_llm(
                model_name=self.config.runner.supervisor_node.model_name,
                prompt_cache_key=self.config.runner.supervisor_node.prompt_cache_key,
            ),
            prompt_text=process_prompt.SUPERVISOR_NODE_PROMPT,
            make_inputs=process_prompt.make_supervisor_node_inputs,
            parser_output=process_prompt.SupervisorParser,
            state_key="supervisor_result",
            state_append=False,
            node_name="SUPERVISOR_NODE",
        )
        routers["supervisor"] = process_prompt.route_supervisor

        nodes["feedback"] = graph_module.make_normal_node(
            llm=self._get_llm(
                model_name=self.config.runner.feedback_node.model_name,
                prompt_cache_key=self.config.runner.feedback_node.prompt_cache_key,
            ),
            prompt_text=process_prompt.FEEDBACK_NODE_PROMPT,
            make_inputs=process_prompt.make_feedback_node_inputs,
            parser_output=process_prompt.FeedbackParser,
            state_key="feedback_result",
            state_append=False,
            node_name="FEEDBACK_NODE",
        )

        nodes["goal_decomp"] = graph_module.make_normal_node(
            llm=self._get_llm(
                model_name=self.config.runner.goal_decomp_node.model_name,
                prompt_cache_key=self.config.runner.goal_decomp_node.prompt_cache_key,
            ),
            prompt_text=planning_prompt.GOAL_DECOMP_NODE_PROMPT,
            make_inputs=planning_prompt.make_goal_decomp_node_inputs,
            parser_output=planning_prompt.GoalDecompNodeParser,
            state_key="subgoals",
            state_append=False,
            node_name="GOAL_DECOMP_NODE",
        )
        nodes["task_decomp"] = graph_module.make_normal_node(
            llm=self._get_llm(
                model_name=self.config.runner.task_decomp_node.model_name,
                prompt_cache_key=self.config.runner.task_decomp_node.prompt_cache_key,
            ),
            prompt_text=planning_prompt.TASK_DECOMP_NODE_PROMPT,
            make_inputs=planning_prompt.make_task_decomp_node_inputs,
            parser_output=planning_prompt.TaskDecompNodeParser,
            state_key="tasks",
            state_append=False,
            node_name="TASK_DECOMP_NODE",
        )

        nodes["question_answer"] = graph_module.make_normal_node(
            llm=self._get_llm(
                model_name=self.config.runner.question_answer_node.model_name,
                prompt_cache_key=self.config.runner.question_answer_node.prompt_cache_key,
            ),
            prompt_text=process_prompt.QUESTION_ANSWER_NODE_PROMPT,
            make_inputs=process_prompt.make_question_answer_node_inputs,
            parser_output=process_prompt.QuestionAnswerParser,
            state_key="question_answers",
            state_append=True,
            node_name="QUESTION_ANSWER_NODE",
        )

        return graph_module.make_supervised_plan_graph(
            state_schema=StateSchema,
            nodes=nodes,
            routers=routers,
            thread_id="supervised_planning",
        )
