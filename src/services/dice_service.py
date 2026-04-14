"""
DCC Dice Roller — pure business logic.

No MCP, no I/O framework dependency. This module can be imported freely by
tests, CLIs, or any transport layer (MCP, HTTP, gRPC …).

All public functions return typed dataclasses and raise ValueError on invalid
input instead of embedding error text in the return value.
"""

import random
import re
from dataclasses import dataclass

from rulesets.dcc import DICE_CHAIN, CHARACTER_ABILITIES


@dataclass
class DiceRollResult:
    """Result of a single roll_dice call."""
    expression: str
    sides: int
    count: int
    modifier: int
    rolls: list[int]
    subtotal: int   # sum of dice before modifier
    total: int      # subtotal + modifier


@dataclass
class DiceChainResult:
    """Result of a roll_dice_chain call."""
    requested_die: int
    actual_die: int
    steps: int
    clamped: bool
    roll: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _roll_die(sides: int) -> int:
    return random.randint(1, sides)


def _roll_many(sides: int, count: int) -> list[int]:
    return [_roll_die(sides) for _ in range(count)]


def _parse_expression(expression: str) -> tuple[int, int, int]:
    """
    Parse standard dice expression into (count, sides, modifier).
    Accepts: 'd6', '2d6', '1d20+5', '3d8-1', '2d14', etc.
    Raises ValueError if the expression is invalid.
    """
    pattern = r"^(\d*)d(\d+)([+-]\d+)?$"
    m = re.match(pattern, expression.strip().lower())
    if not m:
        raise ValueError(
            f"Invalid dice expression: '{expression}'. "
            "Use a format like '2d6', '1d20+5', or 'd4'."
        )
    count_str, sides_str, mod_str = m.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    modifier = int(mod_str) if mod_str else 0
    return count, sides, modifier


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def roll_dice(expression: str) -> DiceRollResult:
    """
    Roll dice using standard expression and return a DiceRollResult.

    Supports any die size, including the DCC funky dice:
      d3, d4, d5, d6, d7, d8, d10, d12, d14, d16, d20, d24, d30, d100

    Examples of valid expression:
      '1d20'        — roll one d20
      'd6'          — shorthand for 1d6
      '2d6+3'       — roll 2d6 and add 3
      '1d20-2'      — roll 1d20 and subtract 2
      '3d14'        — roll three of DCC's funky d14
      '1d100'       — percentile roll

    Args:
        expression: Dice expression in NdS[+/-M] format.

    Raises:
        ValueError: If the expression is invalid or out of allowed range.
    """
    count, sides, modifier = _parse_expression(expression)

    if not (1 <= count <= 100):
        raise ValueError("Number of dice must be between 1 and 100.")
    if sides < 2:
        raise ValueError("A die must have at least 2 sides.")

    rolls = _roll_many(sides, count)
    subtotal = sum(rolls)
    return DiceRollResult(
        expression=expression,
        sides=sides,
        count=count,
        modifier=modifier,
        rolls=rolls,
        subtotal=subtotal,
        total=subtotal + modifier,
    )


def roll_ability_scores(method: str = "3d6", abilities: list[str] = CHARACTER_ABILITIES) -> dict[str, int]:
    """
    Roll a full set of ability scores for a Dungeon Crawl Classics character.

    DCC attributes (in order): Strength, Agility, Stamina, Personality,
    Intelligence, Luck.  Note that Luck is unique to DCC and used for
    Luck burns and special checks.

    Available methods:
      '3d6'   — Roll 3d6 straight for each ability, in order (classic DCC).
      '4d6dl' — Roll 4d6, drop the lowest die, for each ability.

    Args:
        method: Generation method — '3d6' (default) or '4d6dl'.
        abilities: List of ability names to generate scores for. Defaults to CHARACTER_ABILITIES.

    Raises:
        ValueError: If method is not '3d6' or '4d6dl'.
    """
    if method not in ("3d6", "4d6dl"):
        raise ValueError(f"Unknown method '{method}'. Choose '3d6' or '4d6dl'.")
    scores: dict[str, int] = {}
    for ability in abilities:
        if method == "4d6dl":
            rolls = _roll_many(6, 4)
            scores[ability] = sum(sorted(rolls)[1:])  # drop lowest
        else:  # 3d6
            scores[ability] = sum(_roll_many(6, 3))
    return scores


def roll_dice_chain(starting_die: int, steps: int = 0) -> DiceChainResult:
    """
    Roll using the DCC dice chain, optionally stepping up or down.

    The DCC dice chain determines which die to use based on a character's
    class, level, and situation modifiers. Stepping up improves the die;
    stepping down weakens it.

    Full DCC dice chain (weakest → strongest):
      d3 → d4 → d5 → d6 → d7 → d8 → d10 → d12 → d14 → d16 → d20 → d24 → d30 → d100

    Examples:
      starting_die=6, steps=0  → roll 1d6  (no change)
      starting_die=6, steps=2  → roll 1d8  (stepped up twice)
      starting_die=8, steps=-1 → roll 1d7  (stepped down once)

    Args:
        starting_die: The base die size (e.g., 6 for d6, 20 for d20).
        steps:        Steps up (+) or down (-) the chain. Default is 0.

    Raises:
        ValueError: If starting_die is not a valid die in the DCC chain.
    """
    if starting_die not in DICE_CHAIN:
        valid = ", ".join(f"d{d}" for d in DICE_CHAIN)
        raise ValueError(
            f"d{starting_die} is not a valid DCC die. Valid dice: {valid}"
        )

    idx = DICE_CHAIN.index(starting_die)
    new_idx = idx + steps
    clamped = new_idx < 0 or new_idx >= len(DICE_CHAIN)
    new_idx = max(0, min(len(DICE_CHAIN) - 1, new_idx))
    actual_die = DICE_CHAIN[new_idx]

    return DiceChainResult(
        requested_die=starting_die,
        actual_die=actual_die,
        steps=steps,
        clamped=clamped,
        roll=_roll_die(actual_die),
    )
