"""
DCC Scene Manager MCP Server — transport layer only.

Wraps services/scene_service.py as MCP tools. Generates the party at startup
and exposes tools for the LLM to read and modify party state throughout the
session. State is kept in-memory for the lifetime of this subprocess.

This file is executed as a subprocess entry point by game_master.py, so it
inserts the src/ directory into sys.path to make sibling packages visible.
"""

import os
import sys

_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from mcp.server.fastmcp import FastMCP  # noqa: E402

import services.scene_service as _scene  # noqa: E402
from services.character_service import Condition, format_sheet  # noqa: E402

# Generate the party the moment the server starts.
_scene.generate_party(4)

mcp = FastMCP("DCC Scene Manager")


@mcp.tool()
def get_party_stubs() -> str:
    """
    Return a JSON array of minimal descriptors for each party member.

    Each element has keys: id, race, occupation.
    Use this internally when you need character IDs without the full party display.
    """
    import json as _json
    return _json.dumps(_scene.get_party_stubs())


@mcp.tool()
def set_party_member_identity(
    character_id: str,
    name: str | None = None,
    gender: str | None = None,
    alignment: str | None = None,
) -> str:
    """
    Set the name, gender, and/or alignment for a party member by their ID.

    Parameters:
        character_id: The 8-character internal ID of the character.
        name:         New name (optional).
        gender:       One of: Male, Female, Non-binary (optional).
        alignment:    One of: Chaotic, Neutral, Lawful (optional).
    """
    try:
        ch = _scene.set_character_identity(character_id, name=name, gender=gender, alignment=alignment)
        parts = []
        if name is not None:
            parts.append(f"name='{ch.name}'")
        if gender is not None:
            parts.append(f"gender='{ch.gender}'")
        if alignment is not None:
            parts.append(f"alignment='{ch.alignment}'")
        return f"Updated {ch.name}: {', '.join(parts)}."
    except (KeyError, ValueError) as exc:
        return f"[Scene error] {exc}"


@mcp.tool()
def rename_party_member(character_id: str, new_name: str) -> str:
    """
    Give a party member a proper name, identified by their short ID.

    Parameters:
        character_id: The 8-character internal ID of the character.
        new_name:     The name to assign.
    """
    try:
        ch = _scene.rename_character(character_id, new_name)
        return f"Character {character_id} is now named {ch.name}."
    except KeyError as exc:
        return f"[Scene error] {exc}"


@mcp.tool()
def list_party() -> str:
    """
    Return a summary of all player characters in the current party.

    Use this at the start of the session and whenever you need to know
    who is in the party, their stats, equipment, or active conditions.
    """
    return _scene.format_party()


@mcp.tool()
def get_party_member(name: str) -> str:
    """
    Return the full character sheet for a single party member.

    Parameters:
        name: Character's name (case-insensitive).
    """
    ch = _scene.get_character(name)
    if ch is None:
        return f"[Scene error] No character named '{name}' in the party."
    return format_sheet(ch)


@mcp.tool()
def update_party_member_hp(name: str, delta: int) -> str:
    """
    Adjust a party member's HP (positive = heal, negative = damage).

    Parameters:
        name:  Character name (case-insensitive).
        delta: HP change. Use negative values for damage (e.g., -3).
    """
    try:
        ch = _scene.update_hp(name, delta)
        return f"{ch.name}: HP is now {ch.hp} (changed by {delta:+d})."
    except KeyError as exc:
        return f"[Scene error] {exc}"


@mcp.tool()
def add_party_member_condition(
    name: str,
    condition_name: str,
    source: str = "",
    rounds: int = -1,
) -> str:
    """
    Apply a temporary condition to a party member.

    Parameters:
        name:           Character name (case-insensitive).
        condition_name: Label for the condition (e.g., "poisoned", "on fire").
        source:         What caused it (e.g., "Giant Spider bite").
        rounds:         Duration in rounds; -1 means indefinite.
    """
    try:
        condition = Condition(
            name=condition_name,
            rounds=rounds,
            source=source,
        )
        ch = _scene.add_condition(name, condition)
        duration = "indefinitely" if rounds == -1 else f"for {rounds} round(s)"
        return f"Condition '{condition_name}' applied to {ch.name} {duration}."
    except KeyError as exc:
        return f"[Scene error] {exc}"


@mcp.tool()
def get_leader() -> str:
    """
    Return a short description of the party leader.

    The leader is always the first character in the party and the sole
    protagonist the GM should focus narration on.
    """
    ch = _scene.get_leader()
    if ch is None:
        return "The party is empty — no leader."
    calling_str = ch.calling or "0-level funnel"
    return (
        f"LEADER: {ch.name} — {ch.race} {ch.gender} {ch.alignment} "
        f"{ch.occupation} ({calling_str}). "
        "Narrate the session through this character's perspective."
    )


@mcp.tool()
def remove_party_member_condition(name: str, condition_name: str) -> str:
    """
    Remove a condition from a party member.

    Parameters:
        name:           Character name (case-insensitive).
        condition_name: Condition to remove (case-insensitive).
    """
    try:
        ch, removed = _scene.remove_condition(name, condition_name)
        if removed == 0:
            return f"Condition '{condition_name}' not found on {ch.name}."
        return f"Condition '{condition_name}' removed from {ch.name}."
    except KeyError as exc:
        return f"[Scene error] {exc}"


if __name__ == "__main__":
    mcp.run()
