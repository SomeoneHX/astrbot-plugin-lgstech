"""Core logic for the LGS Tool Bot AstrBot plugin.

These modules are intentionally decoupled from AstrBot: they only yield plain
``str`` replies or :class:`ImageResult` payloads. The plugin entry point
(``main.py``) is responsible for turning those into ``AstrMessageEvent`` replies.
"""

from __future__ import annotations

__all__ = ["ImageResult"]


class ImageResult:
    """A binary image (PNG bytes) that the plugin should send back to the user."""

    def __init__(self, data: bytes):
        self.data = data
