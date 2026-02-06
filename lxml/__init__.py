"""
Lightweight stub for the `lxml` package.

`robocasa` uses `lxml.etree` for XML manipulation in texture swapping scripts.
We don't need full lxml features here; providing an ElementTree-backed subset
keeps imports working without pulling the compiled dependency.
"""

from __future__ import annotations

from . import etree  # noqa: F401

__all__ = ["etree"]

