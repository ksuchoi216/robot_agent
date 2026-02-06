"""
Minimal stub for the `cv2` (OpenCV) module.

`robosuite` imports an OpenCV-based viewer unconditionally, even if you don't use it.
To keep this workspace dependency-light (no network installs), we provide a small
subset of the API as no-ops so imports succeed.
"""

from __future__ import annotations


def imshow(*args, **kwargs) -> None:  # noqa: D401
    """No-op stub."""


def moveWindow(*args, **kwargs) -> None:  # noqa: N802
    """No-op stub."""


def waitKey(delay: int = 0):  # noqa: N802
    """No-op stub. Returns -1 (no key)."""

    return -1


def destroyWindow(*args, **kwargs) -> None:  # noqa: N802
    """No-op stub."""

