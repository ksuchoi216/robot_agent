"""Planner graph wiring the LangGraph Goal -> Task pipeline."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
)

from langchain_community.llms import LlamaCpp
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langfuse.model import TextPromptClient

# from langgraph.graph import END, START, StateGraph
from loguru import logger

from ..utils.enums import ModelNames

if TYPE_CHECKING:
    from .config import LlamaNodeConfig, OpenAINodeConfig

StateCallable = Callable[[Any], Any]
ChainBuild = Tuple[Any, Optional[Any], Optional[str]]


def _create_llm(llm_node_config: Union["OpenAINodeConfig", "LlamaNodeConfig"]):
    if llm_node_config.model_type == "openai":
        if llm_node_config.model_name not in ModelNames._value2member_map_:
            raise ValueError(f"Invalid model name: {llm_node_config.model_name}")

        model = ModelNames(llm_node_config.model_name).value
        llm_kwargs: Dict[str, Any] = {"model": model}
        if llm_node_config.temperature is not None:
            llm_kwargs["temperature"] = llm_node_config.temperature
        if llm_node_config.prompt_cache_key:
            llm_kwargs["extra_body"] = {
                "prompt_cache_key": llm_node_config.prompt_cache_key
            }
        return ChatOpenAI(**llm_kwargs)
    if llm_node_config.model_type == "llama":
        llama_kwargs: Dict[str, Any] = {"model_path": llm_node_config.model_path}
        if llm_node_config.temperature is not None:
            llama_kwargs["temperature"] = llm_node_config.temperature
        if llm_node_config.n_ctx is not None:
            llama_kwargs["n_ctx"] = llm_node_config.n_ctx
        if llm_node_config.n_gpu_layers is not None:
            llama_kwargs["n_gpu_layers"] = llm_node_config.n_gpu_layers
        if llm_node_config.n_threads is not None:
            llama_kwargs["n_threads"] = llm_node_config.n_threads
        if llm_node_config.verbose is not None:
            llama_kwargs["verbose"] = llm_node_config.verbose
        return LlamaCpp(**llama_kwargs)
    raise ValueError(f"Unsupported model_type: {llm_node_config.model_type}")


def _build_llm_chain(
    *,
    llm_node_config: "OpenAINodeConfig | LlamaNodeConfig",
    prompt_input: str | TextPromptClient,
    output_format=None,
) -> ChainBuild:
    llm = _create_llm(llm_node_config)
    if isinstance(prompt_input, TextPromptClient):
        prompt = PromptTemplate.from_template(
            prompt_input.get_langchain_prompt(),
            metadata={"langfuse_prompt": prompt_input},
        )
    else:
        prompt = PromptTemplate.from_template(prompt_input)
    if output_format == "str":
        parser: Optional[Any] = StrOutputParser()
        format_instructions = None
    elif output_format is not None:
        parser = PydanticOutputParser(pydantic_object=output_format)
        format_instructions = parser.get_format_instructions()
    else:
        parser = None
        format_instructions = None

    chain = prompt | llm
    if parser is not None:
        chain = chain | parser
    return chain, parser, format_instructions


def _apply_result_to_state(
    *,
    state: Dict[str, Any],
    result: Any,
    state_type: Literal["dict", "list", "str"],
    state_dict_key: str | None,
    state_return_key: str,
) -> None:
    if state_type == "str":
        state[state_return_key] = result
        return
    if state_type == "list":
        state[state_return_key].append(result)
        return
    if state_type == "dict":
        if state_dict_key is None:
            raise ValueError("dict_key must be provided when state_type is 'dict'")
        logger.info(
            "Updating state[%s][%s] with result.", state_return_key, state_dict_key
        )
        state[state_return_key][state_dict_key] = result
        return
    raise ValueError(f"Unsupported state_type: {state_type}")


def make_llm_node(
    llm_node_config: "OpenAINodeConfig | LlamaNodeConfig",
    *,
    prompt_input: str | TextPromptClient,
    make_inputs: Callable,
    output_format=None,
    state_type: Literal["dict", "list", "str"] = "str",
    state_dict_key: str | None = None,
    state_return_key: str = "history",
    node_name: str = "NODE",
    on_langfuse: bool = True,
    langfuse_metadata: Dict | None = None,
) -> StateCallable:
    if not hasattr(llm_node_config, "prompt_cache_key"):
        raise ValueError("llm_node_config must have prompt_cache_key attribute")

    chain, parser, format_instructions = _build_llm_chain(
        llm_node_config=llm_node_config,
        prompt_input=prompt_input,
        output_format=output_format,
    )

    langfuse_handler = CallbackHandler() if on_langfuse else None

    def node(state):
        logger.info(f"============= {node_name} ==============")
        inputs = make_inputs(state)
        if format_instructions:
            inputs["format_instructions"] = format_instructions

        result = chain.invoke(
            inputs,
            config={"callbacks": [langfuse_handler], "metadata": langfuse_metadata},
        )

        if isinstance(parser, PydanticOutputParser):
            result = result.model_dump()

        _apply_result_to_state(
            state=state,
            result=result,
            state_type=state_type,
            state_dict_key=state_dict_key,
            state_return_key=state_return_key,
        )

        logger.info(f"AI Answer:\n{result}\n")

        return state

    return node
