"""
DCC Dice Roller MCP Server — transport layer only.

Wraps services/dice_service.py as MCP tools. Each tool catches ValueError
raised by the service and returns it as a plain error string so the LLM
can read and narrate it. All successful results are serialised to strings
here; the service itself deals only in typed dataclasses.

This file is executed as a subprocess entry point by game_master.py, so it
inserts the src/ directory into sys.path to make the sibling packages visible.
"""

import os
import sys

# When spawned as a subprocess the package hierarchy is not on sys.path.
# Insert the src/ directory (parent of this package) so that
# `from services.dice_service import …` resolves correctly.
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from mcp.server.fastmcp import FastMCP  # noqa: E402

from services.dice_service import (  # noqa: E402
    roll_dice as _roll_dice,
    roll_ability_scores as _roll_ability_scores,
    roll_dice_chain as _roll_dice_chain,
)

mcp = FastMCP("DCC Dice Roller")


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _fmt_roll_dice(expression: str) -> str:
    result = _roll_dice(expression)
    rolls_str = ", ".join(str(r) for r in result.rolls)
    out = f"🎲 {result.expression}: [{rolls_str}]"
    if result.modifier > 0:
        out += f" + {result.modifier}"
    elif result.modifier < 0:
        out += f" - {abs(result.modifier)}"
    out += f" = {result.total}"
    if result.count > 1:
        out += f"  (dice sum: {result.subtotal})"
    return out


def _fmt_ability_scores(method: str) -> str:
    scores = _roll_ability_scores(method)
    lines = ["📜 DCC Character Ability Scores:\n"]
    for ability, score in scores.items():
        lines.append(f"  {ability:15s}: {score:2d}")
    return "\n".join(lines)


def _fmt_dice_chain(starting_die: int, steps: int) -> str:
    result = _roll_dice_chain(starting_die, steps)
    out = f"🎲 d{result.actual_die}"
    if result.steps > 0:
        out += f" (stepped UP {result.steps} from d{result.requested_die})"
    elif result.steps < 0:
        out += f" (stepped DOWN {abs(result.steps)} from d{result.requested_die})"
    if result.clamped:
        out += " [clamped at chain boundary]"
    out += f": {result.roll}"
    return out


# ---------------------------------------------------------------------------
# MCP tool registrations
# ---------------------------------------------------------------------------

@mcp.tool()
def roll_dice(expression: str) -> str:
    """
    Roll dice using standard expression and return the individual rolls plus total.

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
    """
    try:
        return _fmt_roll_dice(expression)
    except ValueError as exc:
        return f"[Dice error] {exc}"


@mcp.tool()
def roll_ability_scores(method: str = "3d6") -> str:
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
    """
    try:
        return _fmt_ability_scores(method)
    except ValueError as exc:
        return f"[Dice error] {exc}"


@mcp.tool()
def roll_dice_chain(starting_die: int, steps: int = 0) -> str:
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
    """
    try:
        return _fmt_dice_chain(starting_die, steps)
    except ValueError as exc:
        return f"[Dice error] {exc}"


if __name__ == "__main__":
    mcp.run()
