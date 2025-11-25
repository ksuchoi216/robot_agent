"""Regex-based parsers for MLDT planner outputs."""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple

from .errors import ParsingError
from .logger import get_logger

logger = get_logger(__name__)


def _coerce_to_numbered(text: str) -> str:
    """Convert bullet-like text into a numbered list string."""
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    if not lines:
        return ""

    numbered_lines = []
    for idx, line in enumerate(lines, start=1):
        cleaned = re.sub(r"^\d+\.\s*", "", line)
        numbered_lines.append(f"{idx}. {cleaned}")
    return "\n".join(numbered_lines)


def _extract_matches(text: str, pattern: re.Pattern[str]) -> List[Tuple[int, str]]:
    items: List[Tuple[int, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = pattern.match(line)
        if match:
            idx_str, content = match.groups()
            try:
                idx = int(idx_str)
            except ValueError:
                logger.debug("Skipping non-numeric index '%s' for line: %s", idx_str, line)
                continue
            items.append((idx, content.strip()))
    return items


def parse_numbered_list(
    text: str, pattern: str, *, allow_coerce: bool = True
) -> List[str]:
    """Extract numbered list items using the provided regex pattern."""
    compiled = re.compile(pattern, flags=re.MULTILINE)
    items = _extract_matches(text, compiled)

    if not items and allow_coerce:
        logger.info("Initial parse failed; attempting to reformat response.")
        coerced = _coerce_to_numbered(text)
        if coerced and coerced != text:
            items = _extract_matches(coerced, compiled)

    if not items:
        raise ParsingError(
            "Failed to parse numbered list.",
            details={"pattern": pattern, "text": text},
        )

    ordered = [content for _, content in sorted(items, key=lambda pair: pair[0])]
    return ordered


def parse_goal_output(text: str, pattern: str) -> List[str]:
    """Parse subgoals from Goal-level LLM output."""
    return parse_numbered_list(text, pattern)


def parse_task_output(text: str, pattern: str) -> List[str]:
    """Parse subtasks from Task-level LLM output."""
    return parse_numbered_list(text, pattern)


def parse_action_output(text: str, pattern: str) -> List[str]:
    """Parse primitive actions from Action-level LLM output."""
    return parse_numbered_list(text, pattern)


__all__ = [
    "parse_numbered_list",
    "parse_goal_output",
    "parse_task_output",
    "parse_action_output",
]
