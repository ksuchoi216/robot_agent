"""Utility helpers for configuration, prompts, and filesystem paths."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from .errors import ConfigError, PromptLoadError
from .logger import get_logger

logger = get_logger(__name__)


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str
    temperature: float | None = None
    max_tokens: int = 2048


class RetryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_retries: int = 2


class PathConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_dir: str
    prompt_dir: str


class ParsingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_regex: str
    task_regex: str
    action_regex: str


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm: LLMConfig
    retry: RetryConfig
    paths: PathConfig
    parsing: ParsingConfig


_DEFAULT_CONFIG_CANDIDATES: tuple[Path, ...] = (
    Path(__file__).resolve().parents[2] / "configs" / "config.yaml",
    Path(__file__).resolve().parents[2] / "config" / "config.yaml",
)


def normalize_text(value: str) -> str:
    """Trim leading/trailing whitespace and normalize newlines."""
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


def resolve_path(base_dir: Path, candidate: str | Path) -> Path:
    """Resolve relative paths against a base directory."""
    candidate_path = Path(candidate).expanduser()
    return candidate_path if candidate_path.is_absolute() else base_dir / candidate_path


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_run_output_dir(base_dir: Path) -> Path:
    """Create a timestamped run directory under the provided base path."""
    ensure_directory(base_dir)
    run_dir = base_dir / datetime.now().strftime("run_%Y-%m-%d_%H-%M-%S")
    return ensure_directory(run_dir)


def save_json(path: Path, payload: Any) -> None:
    """Persist JSON with UTF-8 encoding."""
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_prompt(prompt_path: Path) -> str:
    """Load and normalize prompt text from disk."""
    try:
        contents = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PromptLoadError(
            f"Prompt file not found: {prompt_path}", details={"path": str(prompt_path)}
        ) from exc
    except OSError as exc:
        raise PromptLoadError(
            f"Failed to read prompt: {prompt_path}", details={"path": str(prompt_path)}
        ) from exc
    return normalize_text(contents)


def load_prompt_from_dir(prompt_dir: Path, relative_path: str | Path) -> str:
    """Resolve a prompt path relative to the configured prompt directory and load it."""
    target = resolve_path(prompt_dir, relative_path)
    return load_prompt(target)


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ConfigError(
            f"Configuration file not found: {path}", details={"path": str(path)}
        ) from exc
    except OSError as exc:
        raise ConfigError(
            f"Failed to read configuration file: {path}", details={"path": str(path)}
        ) from exc


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """Load planner configuration with validation."""
    candidates: Iterable[Path]
    if config_path is not None:
        candidates = (Path(config_path).expanduser(),)
    else:
        candidates = _DEFAULT_CONFIG_CANDIDATES

    searched = []
    for candidate in candidates:
        searched.append(str(candidate))
        if not candidate.exists():
            continue
        raw_config = _read_yaml(candidate)
        try:
            return AppConfig.model_validate(raw_config)
        except ValidationError as exc:
            raise ConfigError(
                f"Invalid configuration: {exc}", details={"path": str(candidate)}
            ) from exc

    raise ConfigError(
        "Configuration file not found.", details={"searched_paths": searched}
    )


__all__ = [
    "AppConfig",
    "LLMConfig",
    "RetryConfig",
    "PathConfig",
    "ParsingConfig",
    "load_config",
    "load_prompt",
    "load_prompt_from_dir",
    "normalize_text",
    "resolve_path",
    "ensure_directory",
    "make_run_output_dir",
    "save_json",
]
