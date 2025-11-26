"""Structured parsers for MLDT planner outputs."""

from __future__ import annotations

from typing import List

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class PlannerList(BaseModel):
    """Structured list returned by planner nodes."""

    items: List[str] = Field(..., description="Ordered list of planner outputs.")


def create_planner_list_parser() -> PydanticOutputParser[PlannerList]:
    """Instantiate a Pydantic output parser for planner lists."""
    return PydanticOutputParser(pydantic_object=PlannerList)


__all__ = ["PlannerList", "create_planner_list_parser"]
