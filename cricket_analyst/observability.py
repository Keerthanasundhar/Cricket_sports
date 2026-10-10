"""Observability helpers for logging and tracing the cricket analyst."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent


def configure_tracing() -> None:
    """Enable LangChain tracing when API credentials are available.

    This is intentionally passive: if no LangSmith/ LangChain API key is set, the
    runtime continues without tracing and without emitting errors.
    """
    if os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_PROJECT", "cricket-insight-studio")
        os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")


def setup_logging(level: Optional[int] = None) -> logging.Logger:
    """Initialize a project logger with simple console output."""
    logger = logging.getLogger("cricket_analyst")
    if level is None:
        raw_level = os.getenv("CRICKET_LOG_LEVEL", "INFO").upper()
        level = logging._nameToLevel.get(raw_level, logging.INFO)
    logger.setLevel(level)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = setup_logging()
configure_tracing()
