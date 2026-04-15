"""
DCC ruleset constants.

Central place for all Dungeon Crawl Classics rule data:
races, classes, the dice chain, and ability score names.
"""

from models import Equipment, Condition


# DCC playable races.
CHARACTER_RACES: dict[str, float] = {"Human": 0.7, "Elf": 0.1, "Halfling": 0.1, "Dwarf": 0.1}
# Each race maps to a list of (occupation, trained_weapon, trade_good) tuples.
CHARACTER_OCCUPATIONS: dict[str, list[tuple[str, str, str]]] = {
    "Human": [
        ("Alchemist",            "Staff",       "Oil, 1 flask"),
        ("Animal trainer",       "Club",        "Pony"),
        ("Armorer",              "Hammer",      "Iron helmet"),
        ("Astrologer",           "Dagger",      "Spyglass"),
        ("Barber",               "Razor",       "Scissors"),
        ("Beadle",               "Staff",       "Holy symbol"),
        ("Beekeeper",            "Staff",       "Jar of honey"),
        ("Blacksmith",           "Hammer",      "Steel tongs"),
        ("Butcher",              "Cleaver",     "Side of beef"),
        ("Caravan guard",        "Short sword", "Linen, 1 yard"),
        ("Cheesemaker",          "Cudgel",      "Stinky cheese"),
        ("Cobbler",              "Awl",         "Shoehorn"),
        ("Confidence artist",    "Dagger",      "Quality cloak"),
        ("Cooper",               "Crowbar",     "Barrel"),
        ("Costermonger",         "Knife",       "Fruit"),
        ("Cutpurse",             "Dagger",      "Small chest"),
        ("Ditch digger",         "Shovel",      "Fine dirt, 1 lb."),
        ("Dock worker",          "Pole",        "1 late RPG book"),
        ("Farmer",               "Pitchfork",   "Hen"),
        ("Fortune-teller",       "Dagger",      "Tarot deck"),
        ("Gambler",              "Club",        "Dice"),
        ("Gongfarmer",           "Trowel",      "Sack of night soil"),
        ("Grave digger",         "Shovel",      "Trowel"),
        ("Guild beggar",         "Sling",       "Crutches"),
        ("Healer",               "Club",        "Holy water, 1 vial"),
        ("Herbalist",            "Club",        "Herbs, 1 lb."),
        ("Herder",               "Staff",       "Herding dog"),
        ("Hunter",               "Shortbow",    "Deer pelt"),
        ("Indentured servant",   "Staff",       "Locket"),
        ("Jester",               "Dart",        "Silk clothes"),
        ("Jeweler",              "Dagger",      "Gem worth 20 gp"),
        ("Locksmith",            "Dagger",      "Fine tools"),
        ("Mendicant",            "Club",        "Cheese dip"),
        ("Mercenary",            "Longsword",   "Hide armor"),
        ("Merchant",             "Dagger",      "4 gp, 14 sp, 27 cp"),
        ("Miller/baker",         "Club",        "Flour, 1 lb."),
        ("Minstrel",             "Dagger",      "Ukulele"),
        ("Noble",                "Longsword",   "Gold ring worth 10 gp"),
        ("Orphan",               "Club",        "Rag doll"),
        ("Ostler",               "Staff",       "Bridle"),
        ("Outlaw",               "Short sword", "Leather armor"),
        ("Rope maker",           "Knife",       "Rope, 100'"),
        ("Scribe",               "Dart",        "Parchment, 10 sheets"),
        ("Shaman",               "Mace",        "Herbs, 1 lb."),
        ("Slave",                "Club",        "Strange-looking rock"),
        ("Smuggler",             "Sling",       "Waterproof sack"),
        ("Soldier",              "Spear",       "Shield"),
        ("Squire",               "Longsword",   "Steel helmet"),
        ("Tax collector",        "Longsword",   "100 cp"),
        ("Trapper",              "Sling",       "Badger pelt"),
        ("Urchin",               "Stick",       "Begging bowl"),
        ("Wainwright",           "Club",        "Pushcart"),
        ("Weaver",               "Dagger",      "Fine suit of clothes"),
        ("Wizard's apprentice",  "Dagger",      "Black grimoire"),
        ("Woodcutter",           "Handaxe",     "Bundle of wood"),
    ],
    "Elf": [
        ("artisan",        "Staff",        "Clay, 1 lb."),
        ("barrister",      "Quill",        "Book"),
        ("chandler",       "Scissors",     "Candles, 20"),
        ("falconer",       "Dagger",       "Falcon"),
        ("forester",       "Staff",        "Herbs, 1 lb."),
        ("glassblower",    "Hammer",       "Glass beads"),
        ("navigator",      "Shortbow",     "Spyglass"),
        ("sage",           "Dagger",       "Parchment and quill pen"),
    ],
    "Halfling": [
        ("chicken butcher", "Handaxe",     "Chicken meat, 5 lbs."),
        ("dyer",            "Staff",       "Fabric, 3 yards"),
        ("glovemaker",      "Awl",         "Gloves, 4 pairs"),
        ("wanderer",        "Sling",       "Hex doll"),
        ("haberdasher",     "Scissors",    "Fine suits, 3 sets"),
        ("mariner",         "Knife",       "Sailcloth, 2 yards"),
        ("moneylender",     "Short sword", "5 gp, 10 sp, 200 cp"),
        ("trader",          "Short sword", "20 sp"),
        ("vagrant",         "Club",        "Begging bowl"),
    ],
    "Dwarf": [
        ("apothecarist",     "Cudgel", "Steel vial"),
        ("blacksmith",       "Hammer", "Mithril, 1 oz."),
        ("chest-maker",      "Chisel", "Wood, 10 lbs."),
        ("herder",           "Staff",  "Sow"),
        ("miner",            "Pick",   "Lantern"),
        ("mushroom-farmer",  "Shovel", "Sack"),
        ("rat-catcher",      "Club",   "Net"),
        ("stonemason",       "Hammer", "Fine stone, 10 lbs."),
    ],
}

# Weapon stats. Peasant-tool entries use the damage and cost of the like weapon.
# cost_cp is in copper pieces: 1 gp = 100 cp, 1 sp = 10 cp.
WEAPONS: list[Equipment] = [
    # ── Core weapons ─────────────────────────────────────────────────────────
    Equipment(name="Club",        cost_cp=3,     damage="1d4",  tags={"melee", "throwable", "blunt"}),
    Equipment(name="Dagger",      cost_cp=300,   damage="1d4",  tags={"melee", "throwable", "piercing"}),
    Equipment(name="Dart",        cost_cp=5,     damage="1d4",  tags={"throwable", "piercing"}),
    Equipment(name="Handaxe",     cost_cp=400,   damage="1d6",  tags={"melee", "throwable", "slashing"}),
    Equipment(name="Longsword",   cost_cp=1000,  damage="1d8",  tags={"melee", "slashing"}),
    Equipment(name="Mace",        cost_cp=500,   damage="1d6",  tags={"melee", "blunt"}),
    Equipment(name="Short sword", cost_cp=700,   damage="1d6",  tags={"melee", "piercing", "slashing"}),
    Equipment(name="Shortbow",    cost_cp=2500,  damage="1d6",  tags={"two-handed", "piercing"}),
    Equipment(name="Sling",       cost_cp=200,   damage="1d4",  tags={"blunt"}),
    Equipment(name="Spear",       cost_cp=300,   damage="1d8",  tags={"melee", "throwable", "piercing"}),
    Equipment(name="Staff",       cost_cp=50,    damage="1d4",  tags={"melee", "two-handed", "blunt"}),
    # ── Peasant tools (damage and cost of like weapon) ────────────────────────
    Equipment(name="Awl",       cost_cp=30,  damage="1d4",  tags={"melee", "piercing"}),
    Equipment(name="Chisel",    cost_cp=30,  damage="1d4",  tags={"melee", "piercing"}),
    Equipment(name="Cleaver",   cost_cp=150, damage="1d6",  tags={"melee", "slashing"}),
    Equipment(name="Crowbar",   cost_cp=30,  damage="1d4",  tags={"melee", "throwable", "blunt"}),
    Equipment(name="Cudgel",    cost_cp=50,  damage="1d4",  tags={"melee", "blunt"}),
    Equipment(name="Hammer",    cost_cp=3,   damage="1d4",  tags={"melee", "throwable", "blunt"}),
    Equipment(name="Knife",     cost_cp=200, damage="1d4",  tags={"melee", "throwable", "piercing"}),
    Equipment(name="Pick",      cost_cp=3,   damage="1d4",  tags={"melee", "two-handed", "piercing"}),
    Equipment(name="Pitchfork", cost_cp=50,  damage="1d8",  tags={"melee", "two-handed", "piercing"}),
    Equipment(name="Pole",      cost_cp=5,   damage="1d4",  tags={"melee", "two-handed", "blunt", "reach"}),
    Equipment(name="Quill",     cost_cp=1,   damage="1d4",  tags={"throwable", "piercing"}),
    Equipment(name="Razor",     cost_cp=75,  damage="1d4",  tags={"melee", "slashing"}),
    Equipment(name="Scissors",  cost_cp=500, damage="1d4",  tags={"melee", "piercing"}),
    Equipment(name="Shovel",    cost_cp=35,  damage="1d4",  tags={"melee", "two-handed", "blunt"}),
    Equipment(name="Stick",     cost_cp=0,   damage="1d4",  tags={"melee", "blunt"}),
    Equipment(name="Trowel",    cost_cp=25,  damage="1d4",  tags={"melee", "slashing"}),
]


# Armors and shields sourced from CHARACTER_OCCUPATIONS trade goods.
# Each item has the "wearable" tag, a slot location tag, and an AC condition
# with modifier equal to the item's AC bonus above unarmored (10).
ARMORS: list[Equipment] = [
    Equipment(
        name="Leather armor",
        cost_cp=2000,
        tags={"wearable", "body"},
        conditions=[Condition(name="armor", rounds=-1, target="ac", modifier=3)],
    ),
    Equipment(
        name="Hide armor",
        cost_cp=1500,
        tags={"wearable", "body"},
        conditions=[Condition(name="armor", rounds=-1, target="ac", modifier=2)],
    ),
    Equipment(
        name="Shield",
        cost_cp=1000,
        tags={"wearable", "shield"},
        conditions=[Condition(name="shield", rounds=-1, target="ac", modifier=1)],
    ),
    Equipment(
        name="Iron helmet",
        cost_cp=1000,
        tags={"wearable", "head"},
        conditions=[Condition(name="armor", rounds=-1, target="ac", modifier=1)],
    ),
    Equipment(
        name="Steel helmet",
        cost_cp=1500,
        tags={"wearable", "head"},
        conditions=[Condition(name="armor", rounds=-1, target="ac", modifier=1)],
    ),
]


# Non-weapon, non-armor starting equipment sourced from CHARACTER_OCCUPATIONS trade goods.
# Animals and pure currency entries are excluded.
# Duplicates across occupations are collapsed to a single entry.
# cost_cp is in copper pieces: 1 gp = 100 cp, 1 sp = 10 cp.
TOOLS: list[Equipment] = [
    # ── Alchemical & religious ────────────────────────────────────────────────
    Equipment(name="Oil, 1 flask",            cost_cp=3),    # lamp oil, DCC p.73
    Equipment(name="Holy symbol",             cost_cp=25),
    Equipment(name="Holy water, 1 vial",      cost_cp=25),
    # ── Food & consumables ────────────────────────────────────────────────────
    Equipment(name="Jar of honey",            cost_cp=10),
    Equipment(name="Side of beef",            cost_cp=100),
    Equipment(name="Stinky cheese",           cost_cp=3),
    Equipment(name="Fruit",                   cost_cp=2),
    Equipment(name="Cheese dip",              cost_cp=3),
    Equipment(name="Herbs, 1 lb.",            cost_cp=10),
    Equipment(name="Flour, 1 lb.",            cost_cp=2),
    # ── Tools & instruments ───────────────────────────────────────────────────
    Equipment(name="Spyglass",                cost_cp=5000),
    Equipment(name="Steel tongs",             cost_cp=125),
    Equipment(name="Shoehorn",                cost_cp=5),
    Equipment(name="Tarot deck",              cost_cp=250),
    Equipment(name="Dice",                    cost_cp=10),
    Equipment(name="Crutches",                cost_cp=15),
    Equipment(name="Fine tools",              cost_cp=2000),  # locksmith's picks & picks
    Equipment(name="Ukulele",                 cost_cp=1000),
    Equipment(name="Bridle",                  cost_cp=50),
    Equipment(name="Lantern",                 cost_cp=100),
    Equipment(name="Net",                     cost_cp=100),
    Equipment(name="Pushcart",                cost_cp=1000),
    Equipment(name="Steel vial",              cost_cp=150),
    # ── Books & writing ───────────────────────────────────────────────────────
    Equipment(name="Book",                    cost_cp=5000),
    Equipment(name="Parchment, 10 sheets",    cost_cp=200),   # 20 cp/sheet
    Equipment(name="Parchment and quill pen", cost_cp=50),
    Equipment(name="Black grimoire",          cost_cp=10000),
    # ── Containers & storage ─────────────────────────────────────────────────
    Equipment(name="Barrel",                  cost_cp=100),
    Equipment(name="Small chest",             cost_cp=800),
    Equipment(name="Sack",                    cost_cp=5),
    Equipment(name="Waterproof sack",         cost_cp=20),
    # ── Raw materials & trade goods ───────────────────────────────────────────
    Equipment(name="Linen, 1 yard",           cost_cp=5),
    Equipment(name="Rope, 100'",              cost_cp=50),   # DCC 50' = 25 cp
    Equipment(name="Candles, 20",             cost_cp=20),   # 1 cp each
    Equipment(name="Glass beads",             cost_cp=200),
    Equipment(name="Clay, 1 lb.",             cost_cp=2),
    Equipment(name="Fabric, 3 yards",         cost_cp=15),
    Equipment(name="Sailcloth, 2 yards",      cost_cp=15),
    Equipment(name="Wood, 10 lbs.",           cost_cp=5),
    Equipment(name="Bundle of wood",          cost_cp=5),
    Equipment(name="Fine stone, 10 lbs.",     cost_cp=5),
    Equipment(name="Mithril, 1 oz.",          cost_cp=2000), # rare metal ~20 gp/oz
    # ── Pelts & curiosities ───────────────────────────────────────────────────
    Equipment(name="Deer pelt",               cost_cp=50),
    Equipment(name="Badger pelt",             cost_cp=20),
    Equipment(name="Strange-looking rock",    cost_cp=0),
    Equipment(name="Rag doll",                cost_cp=15),
    Equipment(name="Hex doll",                cost_cp=50),
    Equipment(name="Begging bowl",            cost_cp=2),
    Equipment(name="Gem worth 20 gp",         cost_cp=2000), # stated value
    # ── Wearables ─────────────────────────────────────────────────────────────
    Equipment(name="Quality cloak",           cost_cp=200,   tags={"wearable", "shoulders"}),
    Equipment(name="Locket",                  cost_cp=75,    tags={"wearable", "neck"}),
    Equipment(name="Silk clothes",            cost_cp=500,   tags={"wearable", "body"}),
    Equipment(name="Fine suit of clothes",    cost_cp=5000,  tags={"wearable", "body"}),
    Equipment(name="Fine suits, 3 sets",      cost_cp=15000, tags={"wearable", "body"}),
    Equipment(name="Gloves, 4 pairs",         cost_cp=40,    tags={"wearable", "hands"}),
    Equipment(name="Gold ring worth 10 gp",   cost_cp=1000,  tags={"wearable", "ring"}),  # stated value
]


# All DCC classes. Humans choose from Warrior/Wizard/Cleric/Thief.
# Non-human races (Elf, Halfling, Dwarf) use their race name as their class.
CHARACTER_CLASSES: list[str] = ["Warrior", "Wizard", "Cleric", "Thief", "Elf", "Halfling", "Dwarf"]

ALIGNEMENTS: list[str] = ["Chaotic", "Neutral", "Lawful"]

GENDERS: list[str] = ["Male", "Female"]

# Equipment slots. ring_left / ring_right are the two ring slots.
# Items tagged 'two-handed' require both 'weapon' and 'shield' to be empty.
SLOTS: list[str] = [
    "head", "shoulders", "back", "body",
    "weapon", "shield",
    "ring_left", "ring_right",
    "neck", "feet", "belt",
]

# The full DCC dice chain, weakest → strongest.
DICE_CHAIN: list[int] = [3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 20, 24, 30, 100]

# DCC ability names differ from standard D&D.
CHARACTER_ABILITIES: list[str] = [
    "Strength",
    "Agility",      # DCC uses Agility, not Dexterity
    "Stamina",      # DCC uses Stamina, not Constitution
    "Personality",  # DCC uses Personality, not Wisdom
    "Intelligence",
    "Luck",         # Unique to DCC — used for Luck burns and checks
]

ABILITY_MODIFIERS: dict[int, int] = {
    3: -3,
    4: -2,
    5: -2,
    6: -1,
    7: -1,
    8: -1,
    9: 0,
    10: 0,
    11: 0,
    12: 0,
    13: +1,
    14: +1,
    15: +1,
    16: +2,
    17: +2,
    18: +3,
    19: +3,
    20: +4,
    21: +4,
    22: +5,
    23: +6,
    24: +7,
    25: +8,
}
