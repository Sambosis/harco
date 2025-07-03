"""
src.main
========
Command-line entry point for the *Harford County Clash* strategy simulator.

This module is intentionally thin: it focuses on boot-strapping CLI arguments,
initialising logging, wiring together high-level objects (map → agents →
referee), and then handing control over to the :class:`referee.Referee`
instance.  All heavy-lifting lives elsewhere so that this file remains easy to
reason about and, most importantly, *side-effect free* besides I/O.

Author
------
Harford County Clash maintainers
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Tuple

# Project-local imports
# ---------------------------------------------------------------------------

from referee import Referee
from llm_agent import LLMGameAgent as LLMAgent  # re-exported name in skeleton
from local_map import MapFactory

# --------------------------------------------------------------------------- #
# Configuration & Logging Helpers                                             #
# --------------------------------------------------------------------------- #

LOGGER = logging.getLogger(__name__)
LOG_LEVEL_ENV_VAR: str = "HCC_LOG_LEVEL"
_DEFAULT_LOG_FMT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def _configure_logging() -> None:
    """
    Configure the global :pymod:`logging` machinery.

    The log level can be overridden via the ``HCC_LOG_LEVEL`` environment
    variable (e.g. ``export HCC_LOG_LEVEL=DEBUG``).  If unspecified, *INFO*
    is used as a sensible default.
    """
    level_name: str = os.getenv(LOG_LEVEL_ENV_VAR, "INFO").upper()
    # Fallback to INFO when an invalid level string is provided.
    level: int = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(level=level, format=_DEFAULT_LOG_FMT)
    # Make the root logger slightly less noisy by downgrading extremely chatty
    # third-party libs (e.g., `openai`, `urllib3`).
    logging.getLogger("openai").setLevel(max(level, logging.WARNING))
    logging.getLogger("urllib3").setLevel(max(level, logging.WARNING))


# --------------------------------------------------------------------------- #
# CLI Argument Parsing                                                        #
# --------------------------------------------------------------------------- #

def _build_arg_parser() -> argparse.ArgumentParser:
    """
    Construct and configure the application's :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="harford-county-clash",
        description="Turn-based LLM-vs-LLM strategy game set in Harford County (MD).",
    )

    # General simulation parameters
    parser.add_argument(
        "--turns",
        type=int,
        default=None,
        help="Fixed number of turns to play (default: unlimited until victory).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Deterministic RNG seed enabling reproducible replays.",
    )

    # LLM-related parameters
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-3.5-turbo",
        help="Model name to use for *both* agents.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.8,
        help="Soft-max temperature forwarded to the chat-completion API.",
    )

    # Replay logging
    parser.add_argument(
        "--replay",
        type=str,
        metavar="PATH",
        default=None,
        help="File path to write the JSON replay log.",
    )

    return parser


def _parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Parameters
    ----------
    argv :
        Argument vector to parse, excluding the program name.  Defaults to
        ``sys.argv[1:]`` when *None*.
    """
    parser = _build_arg_parser()
    return parser.parse_args(argv)


# --------------------------------------------------------------------------- #
# Game Initialization Helpers                                                 #
# --------------------------------------------------------------------------- #

def _create_agents(model: str, temperature: float, seed: int | None) -> Tuple[LLMAgent, LLMAgent]:
    """
    Instantiate the two commanders.

    BlueCrabs → *team_id* ``0``  
    BayBirds  → *team_id* ``1``
    """
    system_prompt = (
        "You are the autonomous commander for your faction in a 10×10 grid "
        "war-game taking place in Harford County, Maryland.  "
        "You will be provided with a restricted JSON view of the battlefield.  "
        "Respond *only* with a JSON dictionary mapping each of your unit IDs "
        "to its chosen action for this turn.  Do not reveal private reasoning."
    )

    # Derive deterministic sub-seeds so the two agents aren't identical when a
    # single seed is provided.
    blue_seed = None if seed is None else seed + 1337
    red_seed = None if seed is None else seed + 7331

    blue_agent = LLMAgent(
        team_id=0,
        team_name="BlueCrabs",
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
    )
    red_agent = LLMAgent(
        team_id=1,
        team_name="BayBirds",
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
    )

    # Stash seeds on the instances for downstream determinism—some agent
    # implementations may consume `random` internally.
    blue_agent.seed = blue_seed  # type: ignore[attr-defined]
    red_agent.seed = red_seed    # type: ignore[attr-defined]

    return blue_agent, red_agent


def _create_referee(blue_agent: LLMAgent, red_agent: LLMAgent) -> Referee:
    """
    Wire-up the :class:`referee.Referee` object that governs the simulation.
    """
    # Pass the MapFactory class itself, not the result of calling build_initial_state
    map_obj = MapFactory

    referee = Referee(map_obj, [blue_agent, red_agent])
    return referee


# --------------------------------------------------------------------------- #
# Main Execution Logic                                                        #
# --------------------------------------------------------------------------- #

def run_game(args: argparse.Namespace) -> int:  # noqa: C901 – complexity is fine
    """
    High-level orchestration function.

    Returns
    -------
    int
        OS return code (``0`` on success, ``1`` on fatal error).
    """
    start = time.perf_counter()

    try:
        # Seeding prior to object creation ensures deterministic behaviour in
        # any module that relies on the *global* RNG.
        if args.seed is not None:
            import random

            random.seed(args.seed)

        # 1. Agent construction
        blue_agent, red_agent = _create_agents(args.model, args.temperature, args.seed)
        LOGGER.info("Constructed agents: %s, %s", blue_agent.team_name, red_agent.team_name)

        # 2. Referee + map
        referee = _create_referee(blue_agent, red_agent)
        LOGGER.info("Referee initialised, starting match…")

        # 3. Primary game loop
        max_turns = args.turns if args.turns is not None else 50  # default cap
        referee.run(max_turns=max_turns)

        # 4. Wrap-up / scoreboard (placeholder until Referee exposes richer API)
        LOGGER.info("Match finished in %d turn(s).", max_turns)
        print("\n🏁  Game concluded.  🏁")
        # The real implementation might expose `referee.winner` etc.
        # For now, we simply acknowledge completion.

        duration = time.perf_counter() - start
        LOGGER.info("Total runtime: %.2fs", duration)
        return 0

    except KeyboardInterrupt:
        LOGGER.warning("Simulation interrupted by user.")
        return 1
    except Exception as exc:  # noqa: BLE001 – broad to convert to exit-code
        LOGGER.exception("Fatal error during simulation: %s", exc)
        return 1


def main(argv: list[str] | None = None) -> int:
    """
    Module-level entry point used by both ``python -m src.main`` and the
    ``console_scripts`` packaging shim.
    """
    _configure_logging()
    args = _parse_cli_args(argv)
    return run_game(args)


# --------------------------------------------------------------------------- #
# Standard Library Entrypoint                                                 #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())