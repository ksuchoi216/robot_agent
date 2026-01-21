from langfuse import get_client
from langgraph.graph import END, START, StateGraph

from ...common.nodes import make_llm_node
from .config import config
from .state import StateSchema


def make_coach_node_input(state):
    return {
        "data_dict": state["input_dict"],
    }


def create_graph():

    # * nodes -------------------------------------------------
    langfuse = get_client()
    coach_node = make_llm_node(
        llm_node_config=config.coach_node,
        # prompt_input=prompt.COACH_NODE_PROMPT,
        prompt_input=langfuse.get_prompt("report_node"),
        make_inputs=make_coach_node_input,
        output_format="str",
        state_type="str",
        state_return_key="result",
        node_name="coach_node",
        langfuse_metadata={
            "langfuse_tags": ["initial", "coach"],
            "langfuse_user_id": "this-is-user-id",
            "langfuse_session_id": "coach_node",
        },
    )

    # * graph definition ---------------------------------------
    workflow = StateGraph(state_schema=StateSchema)
    workflow.add_node("coach_node", coach_node)  # type: ignore

    workflow.add_edge(START, "coach_node")
    workflow.add_edge("coach_node", END)

    graph = workflow.compile(checkpointer=None)
    return graph
