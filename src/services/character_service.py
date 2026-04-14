"""
DCC Character Sheet — pure business logic.

A minimal 0-level DCC character sheet. Ability score keys match CHARACTER_ABILITIES
from rulesets/dcc.py. Loads from / saves to a JSON file via marshmallow schemas;
no I/O framework dependency so it can be used by tests, CLIs, or any transport layer.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from marshmallow import Schema, fields, post_load, pre_load, EXCLUDE

from rulesets.dcc import CHARACTER_ABILITIES, ABILITY_MODIFIERS


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Condition:
    """
    A temporary status effect on a character.

    Attributes:
        name:        Label for the condition (e.g., "poisoned", "blind").
        rounds:      How many rounds remain. -1 means indefinite.
        source:      What caused it (e.g., "Giant Spider bite").
        modifier:    Optional numeric modifier to apply while the condition is active (e.g., -2 to all rolls).
        type:        Optional category for the condition (e.g., "poison", "curse", "buff") that can be used for filtering or special interactions.
        """
    name: str
    rounds: int          # -1 = indefinite
    source: str
    modifier: int = 0
    type: str = ""


@dataclass
class Equipment:
    """
    A single item in a character's inventory.

    Attributes:
        name:       Item name (e.g., "Torch", "Healing potion").
        quantity:   How many of this item are carried. Default 1.
        weight:     Item weight in pounds. Default 0.0 (negligible).
        charges:    Number of uses/charges remaining. -1 means unlimited/N/A.
        source:     Where the item came from (e.g., "starting equipment", "looted").
        conditions: Conditions this item grants while equipped/active.
    """
    name: str
    quantity: int = 1
    weight: float = 0.0
    charges: int = -1          # -1 = not applicable
    source: str = "starting equipment"
    conditions: list["Condition"] = field(default_factory=list)


@dataclass
class CharacterSheet:
    id: str = ""
    name: str = "Unknown Adventurer"
    occupation: str = "Peasant"
    race: str = "Human"           # must be in CHARACTER_RACES
    gender: str = "Male"          # must be in GENDERS
    alignment: str = "Neutral"    # must be in ALIGNEMENTS
    calling: str | None = None    # None = 0-level; non-humans use race as class
    level: int = 0
    abilities: dict[str, int] = field(
        default_factory=lambda: {a: 10 for a in CHARACTER_ABILITIES}
    )
    hp: int = 4
    equipment: list[Equipment] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def get_ac(self) -> int:
        """Compute AC = 10 + Agility modifier + sum of armor modifiers.

        Armor modifiers are drawn from conditions of type 'armor' on both
        equipped items and the character directly.
        """
        agility_mod = ABILITY_MODIFIERS.get(self.abilities.get("Agility", 10), 0)
        armor_mod = sum(
            c.modifier
            for eq in self.equipment
            for c in eq.conditions
            if c.type == "armor"
        ) + sum(
            c.modifier
            for c in self.conditions
            if c.type == "armor"
        )
        return 10 + agility_mod + armor_mod


# ---------------------------------------------------------------------------
# Marshmallow schemas
# ---------------------------------------------------------------------------

class ConditionSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name        = fields.Str(load_default="unknown")
    rounds      = fields.Int(load_default=-1)
    source      = fields.Str(load_default="")

    @post_load
    def make(self, data, **kwargs) -> Condition:
        return Condition(**data)


class EquipmentSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name       = fields.Str(load_default="unknown")
    quantity   = fields.Int(load_default=1)
    weight     = fields.Float(load_default=0.0)
    charges    = fields.Int(load_default=-1)
    source     = fields.Str(load_default="starting equipment")
    conditions = fields.List(fields.Nested(lambda: ConditionSchema()), load_default=list)

    @post_load
    def make(self, data, **kwargs) -> Equipment:
        return Equipment(**data)


class CharacterSheetSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id         = fields.Str(load_default="")
    name       = fields.Str(load_default="Unknown Adventurer")
    occupation = fields.Str(load_default="Peasant")
    race       = fields.Str(load_default="Human")
    gender     = fields.Str(load_default="Male")
    alignment  = fields.Str(load_default="Neutral")
    calling    = fields.Str(load_default=None, allow_none=True)
    level      = fields.Int(load_default=0)
    abilities  = fields.Dict(keys=fields.Str(), values=fields.Int(), load_default=None)
    hp         = fields.Int(load_default=4)
    equipment  = fields.List(fields.Nested(EquipmentSchema), load_default=list)
    conditions = fields.List(fields.Nested(ConditionSchema), load_default=list)
    notes      = fields.List(fields.Str(), load_default=list)

    @pre_load
    def derive_calling(self, data, **kwargs) -> dict:
        race = data.get("race", "Human")
        if not data.get("calling"):
            data["calling"] = race if race != "Human" else None
        return data

    @post_load
    def make(self, data, **kwargs) -> CharacterSheet:
        if data["abilities"] is None:
            data["abilities"] = {a: 10 for a in CHARACTER_ABILITIES}
        return CharacterSheet(**data)


_schema = CharacterSheetSchema()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_sheet(path: Path) -> CharacterSheet:
    """
    Load a CharacterSheet from a JSON file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file contains invalid JSON or schema errors.
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

    return cast(CharacterSheet, _schema.load(data))


def save_sheet(sheet: CharacterSheet, path: Path) -> None:
    """
    Persist a CharacterSheet to a JSON file.

    Raises:
        OSError: If the file cannot be written.
    """
    data = _schema.dump(sheet)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def format_sheet(sheet: CharacterSheet) -> str:
    """Return the character sheet as a human-readable string."""
    class_str = sheet.calling or "(0-level, no calling)"
    id_str = f"  [{sheet.id}]" if sheet.id else ""
    lines = [
        f"Name:       {sheet.name}{id_str}",
        f"Race:       {sheet.race}   Gender: {sheet.gender}   Alignment: {sheet.alignment}",
        f"Calling:    {class_str}  (Level {sheet.level})",
        f"Occupation: {sheet.occupation}",
        f"HP: {sheet.hp}   AC: {sheet.get_ac()}",
        "",
        "Ability Scores:",
    ]
    for ability in CHARACTER_ABILITIES:
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
            for c in e.conditions:
                rounds_str = "indefinite" if c.rounds == -1 else f"{c.rounds} round(s)"
                lines.append(f"      [{c.name}] {rounds_str}")
    if sheet.conditions:
        lines.append("")
        lines.append("Conditions:")
        for c in sheet.conditions:
            rounds_str = "indefinite" if c.rounds == -1 else f"{c.rounds} round(s)"
            lines.append(f"  [{c.name}] {rounds_str} | source: {c.source}")
    if sheet.notes:
        lines.append("")
        lines.append("Notes:")
        lines.append("  " + "\n  ".join(sheet.notes))
    return "\n".join(lines)
