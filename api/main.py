"""Backward-compatible API entry point for W3.

The canonical W4 FastAPI application lives in src.api.main.
"""

from src.api.main import app

__all__ = ["app"]
