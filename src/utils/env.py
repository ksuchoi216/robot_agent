import os
from pathlib import Path
from typing import Iterable, Optional, Union

from dotenv import load_dotenv

from ..common.logger import get_logger

MODULE_ENV = Path(__file__).resolve().parents[2] / ".env"
DEFAULT_ENV_PATHS: tuple[Path, ...] = (
    Path(".env"),
    MODULE_ENV,
)
LANGSMITH_TRACING_KEY = "LANGSMITH_TRACING"
LANGSMITH_PROJECT_KEY = "LANGSMITH_PROJECT"

SearchInput = Union[str, Path]

logger = get_logger(__name__)


def _as_iterable(candidate: Optional[Union[SearchInput, Iterable[SearchInput]]]):
    if candidate is None:
        return []
    if isinstance(candidate, (str, Path)):
        return [candidate]
    return list(candidate)


def _normalize(candidate: SearchInput) -> Path:
    candidate_path = Path(candidate).expanduser()
    if not candidate_path.is_absolute():
        candidate_path = Path.cwd() / candidate_path
    return candidate_path


def load_env(
    path: Optional[SearchInput] = None,
    *,
    extra_paths: Optional[Iterable[SearchInput]] = None,
    verbose: bool = True,
    langsmith_tracing: bool | None = None,
) -> None:
    """
    Load environment variables from the first existing file in the search order.

    Search order: explicit `path` → `extra_paths` → defaults (`.env`, module `.env`).
    If `langsmith_tracing` is `True`, ensure LangSmith-related variables are set;
    """

    search_order = []
    search_order.extend(_as_iterable(path))
    search_order.extend(_as_iterable(extra_paths))
    search_order.extend(DEFAULT_ENV_PATHS)

    seen = set()
    loaded = False
    for candidate in search_order:
        normalized = _normalize(candidate)
        key = normalized.resolve()
        if key in seen:
            continue
        seen.add(key)

        if normalized.exists():
            load_dotenv(normalized)
            if verbose:
                logger.info("Loaded env from %s", normalized)
            loaded = True
            break

    if langsmith_tracing is True:
        os.environ[LANGSMITH_TRACING_KEY] = "true"
        logger.info(f"LANGSMITH_TRACING: {os.environ[LANGSMITH_TRACING_KEY]}")
        logger.info(
            f"LANGSMITH_PROJECT: {os.environ.get(LANGSMITH_PROJECT_KEY, 'not set')}"
        )
    elif langsmith_tracing is False:
        os.environ[LANGSMITH_TRACING_KEY] = "false"
        logger.info(f"LANGSMITH_TRACING set to false.")
    else:
        logger.info(
            f"LANGSMITH_TRACING is not modified; current value: {os.environ.get(LANGSMITH_TRACING_KEY, 'not set')}"
        )

    if verbose and not loaded:
        logger.info("No .env file found; skipping load.")
