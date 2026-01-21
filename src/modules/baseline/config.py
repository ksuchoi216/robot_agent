from pydantic import BaseModel

from ...common.config import OpenAINodeConfig


class Config(BaseModel):
    coach_node: OpenAINodeConfig


config = Config(
    coach_node=OpenAINodeConfig(
        model_name="gpt-4o-mini",
        prompt_cache_key="coach_node_v1",
    )
)
