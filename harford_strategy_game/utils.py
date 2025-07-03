"""
src/utils.py

Miscellaneous helper utilities used across the Harford County Clash code-base.

The functions contained here are intentionally *low-level* and *stateless* so
they can be freely imported without fear of circular-dependency headaches or
hidden side-effects.
"""

from __future__ import annotations

import enum
import os
import sys
from typing import Final, Tuple, TypeVar, Union, overload

__all__: list[str] = [
    "clamp",
    "direction_to_delta",
    "ANSIColor",
    "colorize",
    "pretty_unit",
    "pretty_tile",
]

# --------------------------------------------------------------------------- #
# Generic helpers                                                             #
# --------------------------------------------------------------------------- #

_T = TypeVar("_T", int, float)


def clamp(value: _T, min_value: _T, max_value: _T) -> _T:
    """
    Constrain *value* to lie between *min_value* and *max_value* (inclusive).

    Parameters
    ----------
    value : int | float
        The value to clamp.
    min_value : int | float
        Lower bound.
    max_value : int | float
        Upper bound.

    Returns
    -------
    int | float
        The clamped value.

    Raises
    ------
    ValueError
        If *min_value* is larger than *max_value*.
    """
    if min_value > max_value:
        raise ValueError(f"min_value ({min_value}) must not exceed max_value ({max_value}).")

    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


# --------------------------------------------------------------------------- #
# Direction utilities                                                         #
# --------------------------------------------------------------------------- #

class Direction(str, enum.Enum):
    """
    Eight-way compass directions plus the sentinel "STAY".

    The enum inherits from *str* for seamless JSON serialisation.
    """

    N: Final[str] = "N"
    NE: Final[str] = "NE"
    E: Final[str] = "E"
    SE: Final[str] = "SE"
    S: Final[str] = "S"
    SW: Final[str] = "SW"
    W: Final[str] = "W"
    NW: Final[str] = "NW"
    STAY: Final[str] = "STAY"


# Pre-computed translation table.
_DIRECTION_DELTAS: dict[Direction, Tuple[int, int]] = {
    Direction.N: (0, -1),
    Direction.NE: (1, -1),
    Direction.E: (1, 0),
    Direction.SE: (1, 1),
    Direction.S: (0, 1),
    Direction.SW: (-1, 1),
    Direction.W: (-1, 0),
    Direction.NW: (-1, -1),
    Direction.STAY: (0, 0),
}


def _coerce_direction(direction: Union[str, Direction]) -> Direction:
    """
    Attempt to convert an arbitrary input into a *Direction* enum.

    Accepts case-insensitive strings or already-typed enum values.
    """
    if isinstance(direction, Direction):
        return direction
    if not isinstance(direction, str):
        raise TypeError(f"direction must be str or Direction, got {type(direction).__name__}.")
    try:
        return Direction(direction.upper())
    except ValueError as exc:  # noqa: B904
        raise KeyError(f"Unrecognised direction '{direction}'.") from exc


@overload
def direction_to_delta(direction: Direction) -> Tuple[int, int]: ...
@overload
def direction_to_delta(direction: str) -> Tuple[int, int]: ...


def direction_to_delta(direction: Union[str, Direction]) -> Tuple[int, int]:
    """
    Translate a compass direction to an *(dx, dy)* offset (grid delta).

    The grid origin *(0, 0)* is the **top-left** corner with *x* growing to
    the right and *y* growing downward – identical to 2-D array indexing.

    Parameters
    ----------
    direction : str | Direction
        One of {'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'STAY'}.

    Returns
    -------
    tuple[int, int]
        (dx, dy) movement offsets.

    Raises
    ------
    KeyError
        If *direction* is not recognised.
    TypeError
        If *direction* is not a `str` or `Direction`.
    """
    dir_enum = _coerce_direction(direction)
    # Guaranteed to exist – thanks to coercion above.
    return _DIRECTION_DELTAS[dir_enum]


# --------------------------------------------------------------------------- #
# ANSI colour helpers                                                         #
# --------------------------------------------------------------------------- #

class ANSIColor(str, enum.Enum):
    """
    Minimal foreground ANSI colour and style codes.
    """

    RESET: Final[str] = "\033[0m"
    BOLD: Final[str] = "\033[1m"

    BLACK: Final[str] = "\033[30m"
    RED: Final[str] = "\033[31m"
    GREEN: Final[str] = "\033[32m"
    YELLOW: Final[str] = "\033[33m"
    BLUE: Final[str] = "\033[34m"
    MAGENTA: Final[str] = "\033[35m"
    CYAN: Final[str] = "\033[36m"
    WHITE: Final[str] = "\033[37m"


def _ansi_supported() -> bool:
    """
    Best-effort heuristic to decide if ANSI colour should be emitted.

    Disables colours when:
        • The 'HCC_NO_COLOR' environment flag is set, OR
        • Output is redirected to a non-TTY stream.
    """
    if os.getenv("HCC_NO_COLOR"):
        return False
    return sys.stdout.isatty()


def colorize(text: str, fg: ANSIColor, *, bold: bool = False) -> str:
    """
    Wrap *text* in ANSI escape sequences for colourised output.

    Parameters
    ----------
    text : str
        Plain text.
    fg : ANSIColor
        Foreground colour.
    bold : bool, default=False
        Apply bold styling (platform-dependent).

    Returns
    -------
    str
        Possibly colourised string (falls back to *text* unchanged when ANSI
        is disabled).
    """
    if not _ansi_supported():
        return text

    prefix = fg.value
    if bold:
        prefix = ANSIColor.BOLD.value + prefix
    return f"{prefix}{text}{ANSIColor.RESET.value}"


# --------------------------------------------------------------------------- #
# Pretty-printing helpers                                                     #
# --------------------------------------------------------------------------- #

# Hard-coded faction → colour mapping.  Add more as the game grows.
_FACTION_COLORS: dict[str, ANSIColor] = {
    "Chesapeake": ANSIColor.BLUE,
    "Susquehanna": ANSIColor.RED,
    # Default fall-back colour:
    "_": ANSIColor.MAGENTA,
}

# Terrain → colour/emoji mapping for spectator view.
_TERRAIN_STYLE: dict[str, tuple[ANSIColor, str]] = {
    "urban": (ANSIColor.YELLOW, "🏙 "),
    "forest": (ANSIColor.GREEN, "🌲 "),
    "water": (ANSIColor.CYAN, "🌊 "),
    "rural": (ANSIColor.WHITE, "🏞 "),
    # Fallback:
    "_": (ANSIColor.WHITE, "  "),
}


def pretty_unit(unit_name: str, faction: str) -> str:
    """
    Produce a colourised symbol for a unit belonging to *faction*.

    The caller is responsible for layout (spacing, alignment); this helper
    only concerns itself with colours and returning a *short* string.
    """
    fg = _FACTION_COLORS.get(faction, _FACTION_COLORS["_"])
    # Limit to at most three visible characters to keep grid tidy.
    display = unit_name[:3].upper()
    return colorize(display, fg, bold=True)


def pretty_tile(location_name: str, terrain: str) -> str:
    """
    Human-friendly representation of a map tile.

    Currently returns the first two characters of *location_name*,
    colourised according to *terrain*, and optionally prefixed with a tiny
    emoji representing that terrain type.
    """
    fg, emoji = _TERRAIN_STYLE.get(terrain, _TERRAIN_STYLE["_"])
    initials = location_name[:2].upper()
    return colorize(f"{emoji}{initials}", fg)