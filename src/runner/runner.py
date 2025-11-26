"""Planner runner wiring the LangGraph Goal -> Task -> Action pipeline."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from ..common.enums import ModelNames
from ..common.errors import GraphInitializeError
from ..common.logger import get_logger
from ..config.config import Config
from . import graph as graph_module
from .state import PlannerState, PlannerStateMaker

logger = get_logger(__name__)


class Runner:
    def __init__(
        self,
        config: Config,
        result_key: str,
        token_information_changed_callback: Callable | None = None,
    ):
        self.config = config
        self.result_key = result_key
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

    def get_result_from_states(self, states, return_last=True):
        state_list = states if isinstance(states, list) else [states]

        def extract_result(state):
            value = state[self.result_key]
            return value[-1] if return_last else value

        def extract_headers(state):
            headers_dict = state.get("headers_dict", {})
            return headers_dict

        results = [extract_result(state) for state in state_list]
        headers = [extract_headers(state) for state in state_list]
        final_result = results[0] if len(results) == 1 else results
        final_headers = headers[0] if len(headers) == 1 else headers

        return {
            "result": final_result,
            "state": state_list,
            "headers": final_headers,
        }

    def invoke(self, state):
        graph, graph_config = self._ensure_graph()
        final_state = graph.invoke(state, graph_config)
        return self.get_result_from_states(final_state)

    async def ainvoke(self, state):
        graph, graph_config = self._ensure_graph()
        final_state = await graph.ainvoke(state, graph_config)
        return self.get_result_from_states(final_state)

    def batch(self, states):
        graph, graph_config = self._ensure_graph()
        final_states = graph.batch(states, graph_config)
        return [self.get_result_from_states(state) for state in final_states]


class PlanRunner(Runner):
    def build_graph(self):
        pass
