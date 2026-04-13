"""
DCC Character Sheet — pure business logic.

A minimal 0-level DCC character sheet. Ability score keys match DCC_ABILITIES
from dice_service.py. Loads from / saves to a JSON file; no I/O framework
dependency so it can be used by tests, CLIs, or any transport layer.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from services.dice_service import DCC_ABILITIES

# JSON file in the working directory (project root when run normally).
DEFAULT_SHEET_PATH = Path("character.json")

# DCC playable races.
DCC_RACES: list[str] = ["Human", "Elf", "Halfling", "Dwarf"]

# All DCC classes. Humans choose from Warrior/Wizard/Cleric/Thief.
# Non-human races (Elf, Halfling, Dwarf) use their race name as their class.
DCC_CLASSES: list[str] = ["Warrior", "Wizard", "Cleric", "Thief", "Elf", "Halfling", "Dwarf"]


@dataclass
class Condition:
    """
    A temporary status effect on a character.

    Attributes:
        name:     Label for the condition (e.g., "poisoned", "blind").
        rounds:   How many rounds remain. -1 means indefinite.
        source:   What caused it (e.g., "Giant Spider bite").
        stat:     Which stat / roll the modifier applies to
                  (e.g., "Strength", "attack", "all saves").
        modifier: The modifier value as a string.
                  Flat bonuses/penalties use +/- notation (e.g., "+2", "-1").
                  Dice-chain steps use the 'dc' suffix (e.g., "+1dc", "-1dc").
    """
    name: str
    rounds: int          # -1 = indefinite
    source: str
    stat: str
    modifier: str


@dataclass
class Equipment:
    """
    A single item in a character's inventory.

    Attributes:
        name:      Item name (e.g., "Torch", "Healing potion").
        quantity:  How many of this item are carried. Default 1.
        weight:    Item weight in pounds. Default 0.0 (negligible).
        charges:   Number of uses/charges remaining. -1 means unlimited/N/A.
        source:    Where the item came from (e.g., "starting equipment", "looted").
    """
    name: str
    quantity: int = 1
    weight: float = 0.0
    charges: int = -1          # -1 = not applicable
    source: str = "starting equipment"


@dataclass
class CharacterSheet:
    id: str = ""
    name: str = "Unknown Adventurer"
    occupation: str = "Peasant"
    race: str = "Human"           # must be in DCC_RACES
    calling: str | None = None  # None = 0-level; non-humans use race as class
    level: int = 0
    abilities: dict[str, int] = field(
        default_factory=lambda: {a: 10 for a in DCC_ABILITIES}
    )
    hp: int = 4
    ac: int = 10
    equipment: list[Equipment] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)


def load_sheet(path: Path = DEFAULT_SHEET_PATH) -> CharacterSheet:
    """
    Load a CharacterSheet from a JSON file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required fields are missing or malformed.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"No character sheet found at '{path}'. "
            "Create a character.json in the project root."
        )
    try:
        data: dict = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in '{path}': {exc}") from exc

    race = data.get("race", "Human")
    calling = data.get("calling") or (race if race != "Human" else None)

    return CharacterSheet(
        id=data.get("id", ""),
        name=data.get("name", "Unknown Adventurer"),
        occupation=data.get("occupation", "Peasant"),
        race=race,
        calling=calling,
        level=int(data.get("level", 0)),
        abilities=data.get("abilities", {a: 10 for a in DCC_ABILITIES}),
        hp=int(data.get("hp", 4)),
        ac=int(data.get("ac", 10)),
        equipment=[
            Equipment(
                name=e.get("name", "unknown"),
                quantity=int(e.get("quantity", 1)),
                weight=float(e.get("weight", 0.0)),
                charges=int(e.get("charges", -1)),
                source=e.get("source", "starting equipment"),
            )
            for e in data.get("equipment", [])
        ],
        conditions=[
            Condition(
                name=c.get("name", "unknown"),
                rounds=int(c.get("rounds", -1)),
                source=c.get("source", ""),
                stat=c.get("stat", ""),
                modifier=c.get("modifier", ""),
            )
            for c in data.get("conditions", [])
        ],
    )


def format_sheet(sheet: CharacterSheet) -> str:
    """Return the character sheet as a human-readable string."""
    class_str = sheet.calling or "(0-level, no calling)"
    id_str = f"  [{sheet.id}]" if sheet.id else ""
    lines = [
        f"Name:       {sheet.name}{id_str}",
        f"Race:       {sheet.race}",
        f"Calling:    {class_str}  (Level {sheet.level})",
        f"Occupation: {sheet.occupation}",
        f"HP: {sheet.hp}   AC: {sheet.ac}",
        "",
        "Ability Scores:",
    ]
    for ability in DCC_ABILITIES:
        score = sheet.abilities.get(ability, "—")
        lines.append(f"  {ability:15s}: {score}")
    if sheet.equipment:
        lines.append("")
        lines.append("Equipment:")
        for e in sheet.equipment:
            parts = [f"x{e.quantity}" if e.quantity != 1 else ""]
            if e.weight > 0:
                parts.append(f"{e.weight} lb")
            if e.charges != -1:
                parts.append(f"{e.charges} charge(s)")
            if e.source != "starting equipment":
                parts.append(f"from: {e.source}")
            detail = "  (" + ", ".join(p for p in parts if p) + ")" if any(parts) else ""
            lines.append(f"  - {e.name}{detail}")
    if sheet.conditions:
        lines.append("")
        lines.append("Conditions:")
        for c in sheet.conditions:
            rounds_str = "indefinite" if c.rounds == -1 else f"{c.rounds} round(s)"
            lines.append(
                f"  [{c.name}] {rounds_str} | source: {c.source} "
                f"| {c.stat} {c.modifier}"
            )
    return "\n".join(lines)
