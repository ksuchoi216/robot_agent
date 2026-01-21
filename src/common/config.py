from typing import Literal

from pydantic import BaseModel, ConfigDict


class OpenAINodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_type: Literal["openai"] = "openai"
    model_name: str
    prompt_cache_key: str | None = None
    temperature: float | None = None


class LlamaNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_type: Literal["llama"] = "llama"
    model_path: str
    prompt_cache_key: str | None = None
    temperature: float | None = None
    n_ctx: int | None = None
    n_gpu_layers: int | None = None
    n_threads: int | None = None
    verbose: bool | None = None
