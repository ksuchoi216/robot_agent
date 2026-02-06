"""
ElementTree-backed subset of `lxml.etree`.

Only the minimal APIs used by this workspace are implemented.
"""

from __future__ import annotations

import xml.etree.ElementTree as _ET
from typing import Any

Element = _ET.Element


def fromstring(text: str | bytes, parser: Any = None):  # noqa: D401
    """Parse XML from a string."""

    return _ET.fromstring(text)


def tostring(element: _ET.Element, *args: Any, **kwargs: Any) -> bytes:  # noqa: D401
    """Serialize element to bytes (utf-8 by default)."""

    # xml.etree's tostring defaults to encoding='us-ascii'. We mimic lxml's
    # byte output by default by forcing utf-8 when not specified.
    if "encoding" not in kwargs:
        kwargs["encoding"] = "utf-8"
    return _ET.tostring(element, *args, **kwargs)


def ElementTree(element: _ET.Element | None = None):  # noqa: N802
    return _ET.ElementTree(element=element)


__all__ = ["Element", "ElementTree", "fromstring", "tostring"]

