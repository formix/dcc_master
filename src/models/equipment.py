from __future__ import annotations

from dataclasses import dataclass, field

from marshmallow import Schema, fields, post_load, EXCLUDE

from models.condition import Condition, ConditionSchema


@dataclass
class Equipment:
    """
    A single item in a character's inventory.

    Attributes:
        name:       Item name (e.g., "Torch", "Healing potion").
        quantity:   How many of this item are carried. Default 1.
        weight:     Item weight in pounds. Default 0.0 (negligible).
        charges:    Number of uses/charges remaining. -1 means unlimited/N/A.
        conditions: Conditions this item grants while equipped/active.
        tags:       Category tags for the item (e.g., ["armor"], ["weapon"]) used for filtering or special interactions.
        damage:     Damage die expression for weapons (e.g., "1d6"). None for non-weapons.
    """
    name: str
    quantity: int = 1
    weight: float = 0.0
    charges: int = -1          # -1 = not applicable
    damage: str | None = None
    backstab: str | None = None
    fumble: str | None = None  # fumble die expression (e.g. "d8"); None = not applicable
    cost_cp: int = 0
    ranges: list[int] = field(default_factory=list)  # [close, medium, long] in feet; empty = melee only
    note: str | None = None
    conditions: list[Condition] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)


class EquipmentSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name            = fields.Str(load_default="unknown")
    quantity        = fields.Int(load_default=1)
    weight          = fields.Float(load_default=0.0)
    charges         = fields.Int(load_default=-1)
    damage          = fields.Str(load_default=None, allow_none=True)
    backstab        = fields.Str(load_default=None, allow_none=True)
    fumble          = fields.Str(load_default=None, allow_none=True)
    cost_cp         = fields.Int(load_default=0)
    ranges          = fields.List(fields.Int(), load_default=list)
    note            = fields.Str(load_default=None, allow_none=True)
    tags            = fields.List(fields.Str(), load_default=list)
    conditions      = fields.List(fields.Nested(lambda: ConditionSchema()), load_default=list)

    @post_load
    def make(self, data, **kwargs) -> Equipment:
        data["tags"] = set(data.get("tags") or [])
        return Equipment(**data)
