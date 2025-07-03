"""
llm_agent.py

Implementation of `LLMGameAgent`, an autonomous commander that delegates
high-level decision making to a Large-Language-Model (LLM).  The class
encapsulates:

• Prompt construction given a fog-of-war limited game view.
• Stateful conversation buffering (system → user ↔ assistant).
• A thin abstraction over ``openai.ChatCompletion.create`` including basic
  retry logic for transient errors.
• Resilient parsing of the assistant's JSON payload with graceful fallback
  to safe no-op actions if the response is malformed or an exception occurs.
"""

from __future__ import annotations

import ast
import copy
import json
import os
import time
from typing import Any, Dict, List, Optional

import openai

# --------------------------------------------------------------------------- #
# Type Aliases                                                                #
# --------------------------------------------------------------------------- #
JSONDict = Dict[str, Any]
Conversation = List[Dict[str, str]]

# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #

# Maximum number of retries (with exponential back-off) on transient
# OpenAI errors such as ``RateLimitError`` or ``APIError``.
_MAX_RETRIES: int = 3
_RETRY_BASE_DELAY_SEC: float = 2.0

# A hard upper-bound on the number of past exchanges kept in memory to
# avoid unbounded token growth.  The *system* message is always preserved.
_MAX_HISTORY_MESSAGES: int = 10

# When all else fails, units fall back to the following default action.
_PASS_INSTRUCTION: JSONDict = {"action": "pass"}


# --------------------------------------------------------------------------- #
# Public Class                                                                #
# --------------------------------------------------------------------------- #
class LLMGameAgent:
    """
    High-level wrapper for an LLM commander participating in the game.

    Parameters
    ----------
    team_id : int | str
        Stable identifier used by the GameEngine to differentiate teams.
    team_name : str
        Human-readable label (e.g., ``"Team Chesapeake"``).
    system_prompt : str
        Root system instruction defining rules of engagement and *strict*
        response guidelines (must output valid JSON, one action per unit,
        etc.).
    model : str, default="gpt-3.5-turbo"
        Underlying model name; may be superseded by the ``OPENAI_MODEL``
        environment variable at runtime.
    temperature : float, default=0.7
        Softmax temperature forwarded to the chat-completion endpoint.
    """

    # --------------------------------------------------------------------- #
    # Construction                                                          #
    # --------------------------------------------------------------------- #
    def __init__(
        self,
        team_id: int | str,
        team_name: str,
        system_prompt: str,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
    ) -> None:
        self.team_id: int | str = team_id
        self.team_name: str = team_name
        self.system_prompt: str = system_prompt.strip()
        self.model: str = os.getenv("OPENAI_MODEL", model)
        self.temperature: float = temperature

        # Conversation history.  The system prompt is *always* the first entry.
        self._conversation: Conversation = [
            {"role": "system", "content": self.system_prompt}
        ]

        # OpenAI key is looked up lazily; raise a descriptive error only when
        # the first API call is attempted.
        self._openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    # --------------------------------------------------------------------- #
    # Public API                                                            #
    # --------------------------------------------------------------------- #
    def decide(self, public_view_dict: JSONDict) -> JSONDict:
        """
        Ask the LLM for the next set of actions given a perspective-limited
        snapshot of the game state.

        Parameters
        ----------
        public_view_dict : dict
            JSON-serialisable structure created by
            ``GameState.serialize_public_view``.

        Returns
        -------
        dict
            Action dictionary keyed by ``unit_id``.  If *any* unrecoverable
            error occurs, a safe all-pass order is returned.
        """
        # Build user message & add to conversation.
        user_msg = self._build_user_message(public_view_dict)
        self._conversation.append(user_msg)

        try:
            # Truncate conversation if it grows too large (keep system + last N).
            if len(self._conversation) > _MAX_HISTORY_MESSAGES + 1:
                # Preserve the system message, drop the oldest user/assistant pair.
                # History layout: [system, msg1, msg2, ..., msgN]
                excess = len(self._conversation) - (_MAX_HISTORY_MESSAGES + 1)
                # Remove *excess* oldest non-system messages.
                self._conversation = (
                    self._conversation[:1] + self._conversation[1 + excess :]
                )

            assistant_text = self._call_llm(self._conversation)
            parsed = self._parse_response(assistant_text)

            if not parsed:
                raise ValueError("Empty or un-parsable response")

            # Attach assistant reply to conversation for context on subsequent turns.
            self._conversation.append(
                {"role": "assistant", "content": assistant_text.strip()}
            )
            return parsed
        except Exception as exc:  # pylint: disable=broad-except
            # Log locally (stdout) — the referee may choose to capture stderr.
            print(
                f"[{self.team_name}] LLM error – falling back to pass orders: {exc}"
            )
            # Also append the error notice to the conversation to give the LLM
            # a chance to self-correct in following turns.
            self._conversation.append(
                {
                    "role": "assistant",
                    "content": f"ERROR: {type(exc).__name__}: {exc}",
                }
            )
            return self._fallback_pass_action(public_view_dict)

    # --------------------------------------------------------------------- #
    # Helper Methods                                                        #
    # --------------------------------------------------------------------- #
    def _build_user_message(self, view: JSONDict) -> Dict[str, str]:
        """
        Convert the current game view into a ChatCompletion "user" message.

        The view is pretty-printed JSON followed by a minimal instruction
        reminding the model to output *only* JSON in the specified format.
        """
        view_json = json.dumps(view, separators=(",", ":"), ensure_ascii=False)
        prompt = (
            "=== BEGIN TURN ===\n"
            "You are provided with a JSON object representing everything your"
            " faction currently sees on the battlefield (fog-of-war applied).\n"
            "Analyse the situation and reply with ONLY a JSON dictionary where"
            " each key is a unit_id and each value is an action object.\n"
            "Valid actions: move, attack, recruit, gather, pass.\n"
            "Example: {\"u1\": {\"action\": \"move\", \"direction\": \"N\"},"
            " \"u2\": {\"action\": \"pass\"}}\n"
            "DO NOT add any additional keys or explanatory text.\n\n"
            f"{view_json}\n"
            "=== END VIEW ==="
        )
        return {"role": "user", "content": prompt}

    def _call_llm(self, messages: Conversation) -> str:
        """
        Forward the conversation to the OpenAI ChatCompletion endpoint with
        basic retry logic for transient failures.
        """
        if not self._openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable not set – cannot contact LLM."
            )

        openai.api_key = self._openai_api_key

        last_err: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                )
                # OpenAI 0.x & 1.x both expose this path; adjust if API changes.
                assistant_text = response.choices[0].message["content"]  # type: ignore[index]
                return str(assistant_text)
            except (openai.error.RateLimitError, openai.error.APIError) as err:
                last_err = err
                delay = _RETRY_BASE_DELAY_SEC * (2**attempt)
                print(
                    f"[{self.team_name}] OpenAI transient error (attempt {attempt + 1}/{_MAX_RETRIES}): {err} – retrying in {delay:.1f}s"
                )
                time.sleep(delay)
            except Exception as err:  # pylint: disable=broad-except
                # These are unexpected; break out immediately.
                raise RuntimeError(f"LLM call failed: {err}") from err

        # If loop exits without returning, raise the last stored error.
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

    def _parse_response(self, response_text: str) -> JSONDict:
        """
        Parse the assistant response using JSON first, then ``ast.literal_eval``
        as a forgiving fallback.  Returns an empty dict on failure.
        """
        response_text = response_text.strip()
        if not response_text:
            return {}

        # Handle code fence blocks like ```json ... ``` or ``` ... ```
        if "```" in response_text:
            # Find content between code fences
            start_fence = response_text.find("```")
            if start_fence != -1:
                # Look for the content after the first fence
                content_start = response_text.find("\n", start_fence)
                if content_start != -1:
                    content_start += 1  # Skip the newline
                    # Find the closing fence
                    end_fence = response_text.find("```", content_start)
                    if end_fence != -1:
                        response_text = response_text[content_start:end_fence].strip()
                    else:
                        # No closing fence, take everything after opening fence
                        response_text = response_text[content_start:].strip()

        if not response_text.startswith('{'):
            # Try to find JSON embedded in text
            start_idx = response_text.find('{')
            if start_idx != -1:
                # Find matching closing brace
                brace_count = 0
                end_idx = start_idx
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == '{':
                        brace_count += 1
                    elif response_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
                if brace_count == 0:
                    response_text = response_text[start_idx:end_idx + 1]

        # Try JSON parsing first (most reliable)
        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback to ast.literal_eval for more forgiving parsing
        try:
            parsed = ast.literal_eval(response_text)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, SyntaxError):
            pass

        # If all parsing attempts fail, return empty dict
        return {}

    def _fallback_pass_action(self, public_view_dict: JSONDict) -> JSONDict:
        """
        Generate a safe fallback action dict where all team units pass.
        
        This is called when LLM parsing fails or an exception occurs.
        """
        fallback_actions: JSONDict = {}
        
        # Extract team units from the public view
        if "units" in public_view_dict and isinstance(public_view_dict["units"], list):
            team_id = str(self.team_id)
            for unit_data in public_view_dict["units"]:
                if isinstance(unit_data, dict) and unit_data.get("team_id") == team_id:
                    unit_id = unit_data.get("id")
                    if unit_id:
                        fallback_actions[unit_id] = copy.deepcopy(_PASS_INSTRUCTION)
        
        return fallback_actions

    # --------------------------------------------------------------------- #
    # Protocol compatibility                                                #
    # --------------------------------------------------------------------- #
    
    @property
    def name(self) -> str:
        """Alias for team_name to match referee expectations."""
        return self.team_name
