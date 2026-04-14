"""
DCC Character Sheet MCP Server — transport layer only.

Wraps services/character_service.py as MCP tools. Each tool catches errors
raised by the service and returns them as a plain string so the LLM can
read and narrate accordingly.

This file is executed as a subprocess entry point by game_master.py, so it
inserts the src/ directory into sys.path to make sibling packages visible.
"""

import os
import sys

_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from mcp.server.fastmcp import FastMCP  # noqa: E402

from services.character_service import (  # noqa: E402
    load_sheet as _load_sheet,
    save_sheet as _save_sheet,
    format_sheet as _fmt_sheet,
    Condition,
    Equipment,
)
from rulesets.dcc import CHARACTER_RACES, CHARACTER_CLASSES, CHARACTER_ABILITIES  # noqa: E402

mcp = FastMCP("DCC Character Sheet")


@mcp.tool()
def get_character_sheet() -> str:
    """
    Return the current player character sheet.

    Reads character.json from the working directory. Use this whenever you
    need to know a character's name, occupation, ability scores, HP, AC,
    or equipment — for example before calling for a saving throw, resolving
    combat, or describing what a character is carrying.
    """
    try:
        sheet = _load_sheet()
        return _fmt_sheet(sheet)
    except (FileNotFoundError, ValueError) as exc:
        return f"[Sheet error] {exc}"


@mcp.tool()
def update_hp(delta: int) -> str:
    """
    Adjust the character's current HP by *delta* (positive = heal, negative = damage).

    Examples:
      delta=−6  →  character takes 6 points of damage.
      delta=3   →  character heals 3 HP.

    Returns the updated HP value, or an error string if the sheet can't be read.
    """
    try:
        sheet = _load_sheet()
        sheet.hp += delta
        _save_sheet(sheet)
        return f"HP updated: {sheet.hp} (changed by {delta:+d})"
    except (FileNotFoundError, ValueError, OSError) as exc:
        return f"[Sheet error] {exc}"


@mcp.tool()
def update_character_stats(
    name: str | None = None,
    occupation: str | None = None,
    race: str | None = None,
    calling: str | None = None,
    level: int | None = None,
    ac: int | None = None,
) -> str:
    """
    Update basic character fields. Only the fields you supply are changed.

    Parameters:
        name:       Character's name.
        occupation: 0-level occupation (e.g., "Blacksmith").
        race:       Must be one of: Human, Elf, Halfling, Dwarf.
        calling:    Class / calling (e.g., "Warrior"). Pass null for 0-level.
        level:      Character level (0 for funnel).
        ac:         Armour Class.

    Returns a summary of the changes, or an error string.
    """
    try:
        sheet = _load_sheet()
        changes: list[str] = []

        if name is not None:
            sheet.name = name
            changes.append(f"name='{name}'")
        if occupation is not None:
            sheet.occupation = occupation
            changes.append(f"occupation='{occupation}'")
        if race is not None:
            if race not in CHARACTER_RACES:
                return f"[Sheet error] Invalid race '{race}'. Valid races: {', '.join(CHARACTER_RACES)}"
            sheet.race = race
            changes.append(f"race='{race}'")
        if calling is not None:
            if calling not in CHARACTER_CLASSES:
                return f"[Sheet error] Invalid calling '{calling}'. Valid callings: {', '.join(CHARACTER_CLASSES)}"
            sheet.calling = calling
            changes.append(f"calling='{calling}'")
        if level is not None:
            sheet.level = level
            changes.append(f"level={level}")
        if ac is not None:
            sheet.ac = ac
            changes.append(f"ac={ac}")

        if not changes:
            return "No changes supplied — character sheet unchanged."

        _save_sheet(sheet)
        return "Updated: " + ", ".join(changes)
    except (FileNotFoundError, ValueError, OSError) as exc:
        return f"[Sheet error] {exc}"


@mcp.tool()
def update_ability_score(ability: str, score: int) -> str:
    """
    Set a single ability score.

    Parameters:
        ability: One of: Strength, Agility, Stamina, Personality, Intelligence, Luck.
        score:   The new score value (typically 3–18, but not enforced).

    Returns the updated score, or an error string.
    """
    try:
        if ability not in CHARACTER_ABILITIES:
            return (
                f"[Sheet error] Unknown ability '{ability}'. "
                f"Valid abilities: {', '.join(CHARACTER_ABILITIES)}"
            )
        sheet = _load_sheet()
        old = sheet.abilities.get(ability, "—")
        sheet.abilities[ability] = score
        _save_sheet(sheet)
        return f"{ability}: {old} → {score}"
    except (FileNotFoundError, ValueError, OSError) as exc:
        return f"[Sheet error] {exc}"


@mcp.tool()
def add_condition(
    name: str,
    source: str = "",
    rounds: int = -1,
    description: str = "",
) -> str:
    """
    Apply a temporary condition to the character.

    Parameters:
        name:        Label for the condition (e.g., "poisoned", "blinded").
        source:      What caused the condition (e.g., "Giant Spider bite").
        rounds:      Duration in rounds. Use −1 for indefinite.
        description: Free-form text describing the condition's effect.

    Returns confirmation, or an error string.
    """
    try:
        sheet = _load_sheet()
        condition = Condition(
            name=name,
            rounds=rounds,
            source=source,
            description=description,
        )
        sheet.conditions.append(condition)
        _save_sheet(sheet)
        duration = "indefinitely" if rounds == -1 else f"for {rounds} round(s)"
        return f"Condition '{name}' applied {duration}."
    except (FileNotFoundError, ValueError, OSError) as exc:
        return f"[Sheet error] {exc}"


@mcp.tool()
def remove_condition(name: str) -> str:
    """
    Remove a condition from the character by name (case-insensitive).

    Parameters:
        name: The condition label to remove (e.g., "poisoned").

    Returns confirmation or an error string if the condition wasn't found.
    """
    try:
        sheet = _load_sheet()
        before = len(sheet.conditions)
        sheet.conditions = [c for c in sheet.conditions if c.name.lower() != name.lower()]
        removed = before - len(sheet.conditions)
        if removed == 0:
            return f"Condition '{name}' not found on the character sheet."
        _save_sheet(sheet)
        return f"Condition '{name}' removed."
    except (FileNotFoundError, ValueError, OSError) as exc:
        return f"[Sheet error] {exc}"


@mcp.tool()
def add_equipment(
    name: str,
    quantity: int = 1,
    weight: float = 0.0,
    charges: int = -1,
    source: str = "looted",
) -> str:
    """
    Add an item to the character's inventory.

    Parameters:
        name:     Item name (e.g., "Torch", "Healing potion").
        quantity: Number of this item to add. Default 1.
        weight:   Weight in pounds. Default 0.0.
        charges:  Uses/charges remaining; -1 means not applicable.
        source:   Where the item came from (e.g., "looted", "purchased").

    Returns confirmation, or an error string.
    """
    try:
        sheet = _load_sheet()
        item = Equipment(
            name=name,
            quantity=quantity,
            weight=weight,
            charges=charges,
            source=source,
        )
        sheet.equipment.append(item)
        _save_sheet(sheet)
        return f"Added {quantity}x '{name}' to inventory."
    except (FileNotFoundError, ValueError, OSError) as exc:
        return f"[Sheet error] {exc}"


@mcp.tool()
def remove_equipment(name: str, quantity: int = 1) -> str:
    """
    Remove an item (or reduce its quantity) from the character's inventory.

    If *quantity* equals or exceeds the item's current quantity, the item is
    removed entirely. Matching is case-insensitive.

    Parameters:
        name:     Item name to remove.
        quantity: How many to remove. Default 1.

    Returns confirmation, or an error string if the item wasn't found.
    """
    try:
        sheet = _load_sheet()
        for i, item in enumerate(sheet.equipment):
            if item.name.lower() == name.lower():
                if quantity >= item.quantity:
                    sheet.equipment.pop(i)
                    _save_sheet(sheet)
                    return f"Removed '{name}' from inventory."
                else:
                    item.quantity -= quantity
                    _save_sheet(sheet)
                    return f"Removed {quantity}x '{name}' (remaining: {item.quantity})."
        return f"Item '{name}' not found in inventory."
    except (FileNotFoundError, ValueError, OSError) as exc:
        return f"[Sheet error] {exc}"


if __name__ == "__main__":
    mcp.run()
