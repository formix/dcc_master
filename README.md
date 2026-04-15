# DCC JUDGE — old-school CLI powered by Ollama + MCP

A command-line Dungeon Crawl Classics (DCC) judge backed by a local
Ollama LLM. All dice rolls are delegated to **Model Context Protocol**
(MCP) servers. The Judge never invents dice results — every roll is real.

```
 ██████╗  ██████╗ ██████╗         ██╗██╗   ██╗██████╗  ██████╗ ███████╗
 ██╔══██╗██╔════╝██╔════╝         ██║██║   ██║██╔══██╗██╔════╝ ██╔════╝
 ██║  ██║██║     ██║              ██║██║   ██║██║  ██║██║  ███╗█████╗
 ██║  ██║██║     ██║         ██   ██║██║   ██║██║  ██║██║   ██║██╔══╝
 ██████╔╝╚██████╗╚██████╗    ╚█████╔╝╚██████╔╝██████╔╝╚██████╔╝███████╗
 ╚═════╝  ╚═════╝ ╚═════╝     ╚════╝  ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝
```

---

## Architecture

```
src/cli/judge.py                   ← main CLI (Ollama tool-calling loop)
    │
    │  MCP stdio transport (subprocess)
    ├──▶ src/servers/dice_server.py   ← FastMCP — 3 dice tools
    └──▶ src/servers/scene_server.py  ← FastMCP — 11 party / scene tools
```

`judge.py` spawns `dice_server.py` and `scene_server.py` as child processes
and communicates with them over stdin/stdout via the MCP protocol. The Ollama
model receives all tool schemas and can call them freely during the session.

```
src/
├── cli/
│   └── judge.py               ← entry point
├── models/
│   ├── character_sheet.py     ← CharacterSheet dataclass + marshmallow schema
│   ├── condition.py           ← Condition dataclass
│   ├── dice_roll.py           ← DiceRollResult / DiceChainResult dataclasses
│   └── equipment.py           ← Equipment dataclass
├── rulesets/
│   └── dcc.py                 ← DCC tables (races, occupations, abilities, …)
├── servers/
│   ├── dice_server.py         ← MCP server: dice tools
│   ├── scene_server.py        ← MCP server: party management tools
│   └── character_server.py    ← MCP server: single-character sheet tools (standalone)
└── services/
    ├── dice_service.py        ← pure dice logic
    ├── scene_service.py       ← in-memory party state
    └── character_service.py   ← character sheet load / save / format
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.10+** | Required by the `mcp` package |
| **[uv](https://docs.astral.sh/uv/)** | Fast Python package manager (recommended) |
| **Ollama** | Local LLM service — <https://ollama.com> |
| A **tool-calling capable model** | See table below |

### Recommended Ollama models

| Model | Pull command | Notes |
|---|---|---|
| `llama3.2` (default) | `ollama pull llama3.2` | Fast, good tool calling |
| `llama3.1` | `ollama pull llama3.1` | Larger, more capable |
| `qwen2.5` | `ollama pull qwen2.5` | Excellent tool calling |
| `mistral-nemo` | `ollama pull mistral-nemo` | Good balance |
| `command-r` | `ollama pull command-r` | Strong at following rules |

---

## Setup

```powershell
# 1. Clone / open the project folder
cd dcc_judge

# 2. Create a virtual environment with uv
uv venv .venv
.venv\Scripts\Activate.ps1       # Windows PowerShell
# source .venv/bin/activate      # macOS / Linux

# 3. Install dependencies
uv pip install -r requirements.txt

# 4. Make sure Ollama is running
ollama serve                     # (in a separate terminal if not running as a service)

# 5. Pull a model (once)
ollama pull llama3.2
```

---

## Running

```powershell
# Default model (llama3.2)
python src/cli/judge.py

# Specify a different model
python src/cli/judge.py qwen2.5
python src/cli/judge.py llama3.1
```

Type **`quit`** or **`exit`** (or press `Ctrl+C`) to end the session.

---

## Session flow

1. **Startup** — both MCP servers are spawned and connected.
2. **Party generation** — 4 random 0-level characters are rolled (race, occupation,
   starting weapon and trade good come from DCC tables).
3. **Customisation** — for each character you choose:
   - *Gender* (Male / Female / Non-binary)
   - *Name* (the LLM suggests a culturally fitting name; press Enter to accept)
   - *Alignment* (Chaotic / Neutral / Lawful)
4. **Opening scene** — GRIMDAR THE UNYIELDING narrates a dramatic opening scene
   woven around the party's occupations. No tool calls on this first turn.
5. **Main loop** — type freely; the Judge calls tools as needed and narrates results.

The **first character** in the party is always the leader. All narration centres
on the leader's perspective; other party members stay in the background.

---

## Local shortcut commands

These are handled directly by the CLI without an LLM round-trip:

| Command | Effect |
|---|---|
| `show party` | Print the full party summary |
| `show <name> inventory` | Print a single character's sheet |
| `equip <name> <item> in <slot>` | Move an item into a worn slot |
| `unequip <name> from <slot>` | Remove the item in a slot back to inventory |

---

## MCP Tools reference

### Dice server — `dice_server.py`

#### `roll_dice(expression)`

Roll any dice using standard NdS±M notation. Used for attacks, saves, damage,
ability checks, and any ad-hoc roll.

| Example | Meaning |
|---|---|
| `1d20` | One d20 |
| `d6` | Shorthand for 1d6 |
| `2d6+3` | Two d6, add 3 |
| `1d20-2` | One d20, subtract 2 |
| `3d14` | Three DCC funky d14s |

All DCC funky dice are supported: **d3 d4 d5 d6 d7 d8 d10 d12 d14 d16 d20 d24 d30 d100**.

#### `roll_ability_scores(method)`

Roll six DCC ability scores: **Strength · Agility · Stamina · Personality · Intelligence · Luck**

| Method | Description |
|---|---|
| `3d6` (default) | Classic straight roll — standard DCC funnel |
| `4d6dl` | Roll 4d6, drop the lowest — slightly heroic |

#### `roll_dice_chain(starting_die, steps)`

Step a die up or down the DCC dice chain (Mighty Deeds, class abilities, conditions).

```
d3 → d4 → d5 → d6 → d7 → d8 → d10 → d12 → d14 → d16 → d20 → d24 → d30 → d100
```

| Argument | Description |
|---|---|
| `starting_die` | Base die size (e.g. `6` for d6) |
| `steps` | Steps up (`+`) or down (`−`) the chain |

---

### Scene server — `scene_server.py`

Manages the in-memory party for the lifetime of the session.

| Tool | Description |
|---|---|
| `get_party_stubs()` | JSON array of `{id, race, occupation}` for each character |
| `set_party_member_identity(character_id, name, gender, alignment)` | Set identity fields by ID |
| `rename_party_member(character_id, new_name)` | Rename a character by ID |
| `list_party()` | Full formatted party summary |
| `get_party_member(name)` | Full character sheet for one member |
| `get_leader()` | Short description of the party leader |
| `update_party_member_hp(name, delta)` | Heal or damage a character (`delta` positive = heal) |
| `add_party_member_condition(name, condition_name, rounds, target, modifier, tags)` | Apply a condition |
| `remove_party_member_condition(name, condition_name)` | Remove a condition |
| `equip_party_member_item(name, item_name, slot)` | Move an item into a worn slot |
| `unequip_party_member_item(name, slot)` | Remove item from a slot back to inventory |

Valid equipment slots: `head · shoulder · back · body · weapon · shield · ring_left · ring_right · neck · feet`

---

## Example session

```
Human blacksmith [1] Chaotic
Human rat-catcher [2] Neutral
...

⚖  GRIMDAR THE UNYIELDING, JUDGE  ⚖
  "The village of Ashwick reeks of desperation. Its mill burned last night
   and three children are missing. The miller, Aldric the blacksmith, grips
   his hammer and stares at the dark tree-line. What do you do?"

You: Aldric checks the mill ruins for tracks.

  🎲 roll_dice(expression='1d20')
  🎲 1d20: [14] = 14

⚖  GRIMDAR THE UNYIELDING, JUDGE  ⚖
  "Sharp eyes, Aldric. You spot clawed prints — three-toed, the size of
   your fist — leading into the Ashwood. They are fresh."
```

---

## Notes

- The judge persona is **GRIMDAR THE UNYIELDING** — edit `SYSTEM_PROMPT` in
  `src/cli/judge.py` to change the tone or house rules.
- Party state lives in-memory for the duration of the session only; nothing is
  persisted to disk between runs.
- `src/servers/character_server.py` is a standalone MCP server for single-player
  character sheet management (not connected by default in the CLI).
