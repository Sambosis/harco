"""
llm_agent.py

Autonomous commander that delegates strategy to an LLM.  When the
OpenAI client (and an API key) are unavailable the agent degrades gracefully by
issuing deterministic "pass" orders for every friendly unit.

"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Std-lib                                                                     #
# --------------------------------------------------------------------------- #
import ast
import json
import os
import time
from typing import Any, Dict, List, Optional, TypedDict

# --------------------------------------------------------------------------- #
# Optional third-party                                                        #
# --------------------------------------------------------------------------- #
try:  # pragma: no cover
    import openai  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    openai = None  # type: ignore

# --------------------------------------------------------------------------- #
# Public aliases & constants                                                  #
# --------------------------------------------------------------------------- #
JSONDict = Dict[str, Any]
ChatMsg = Dict[str, str]
ChatHistory = List[ChatMsg]


class ActionDict(TypedDict, total=False):
    action: str


_DEFAULT_MODEL = "gpt-3.5-turbo"
_DEFAULT_TEMP = 0.7
_PASS: ActionDict = {"action": "pass"}

_HISTORY_LIMIT = 6              # max user/assistant *pairs*
_MAX_RETRIES = 3
_BACKOFF = 2.0                  # seconds


# --------------------------------------------------------------------------- #
# Helper functions                                                            #
# --------------------------------------------------------------------------- #
def _strip_md_fences(text: str) -> str:
    """Remove common markdown fences so json.loads has a chance."""
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
        if text.endswith(fence):
            text = text[:-len(fence)]
    return text


def _get_model(model: str) -> str:
    """
    Get the model name from the environment variable or use the default.
    """
    return os.getenv("OPENAI_MODEL", model)


def _get_temperature(temperature: float) -> float:
    """
    Get the temperature from the environment variable or use the default.
    """
    return float(os.getenv("OPENAI_TEMP", str(temperature)))


def _get_history(history: ChatHistory) -> ChatHistory:
    """
    Get the history from the environment variable or use the default.
    """
    return json.loads(os.getenv("OPENAI_HISTORY", json.dumps(history))) 
