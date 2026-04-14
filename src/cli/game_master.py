"""
DCC Game Master — Command-Line Interface

An old-school Dungeon Crawl Classics game master powered by Ollama and the
DCC Dice Roller and Scene Manager MCP servers. The GM uses real dice rolls (never invented ones)
for all in-game events via the MCP tool calls.

Usage:
    python game_master.py [model]

    model  — Any Ollama model that supports tool calling.
             Defaults to 'llama3.2'. Other good choices: llama3.1, qwen2.5,
             mistral-nemo, command-r.

Prerequisites:
    - Ollama running locally (ollama serve)
    - The chosen model pulled (e.g.: ollama pull llama3.2)
    - Python packages installed (see requirements.txt)
"""

import asyncio
import contextlib
import json
import os
import random
import re
import sys
from collections.abc import Awaitable, Callable

# Ensure src/ is on the path so sibling packages (rulesets, services, …) resolve
# regardless of the working directory the script is launched from.
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import ollama
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.types import TextContent
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.text import Text
from rulesets.dcc import GENDERS, ALIGNEMENTS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "llama3.2"

SYSTEM_PROMPT = """\
You are GRIMDAR THE UNYIELDING, a grizzled and merciless Game Master running a \
Dungeon Crawl Classics (DCC) RPG session. You speak with dramatic flair, drawing \
heavily on Appendix N pulp fantasy: Conan, Elric, Fafhrd and the Gray Mouser. \
You relish in describing grim dungeons, horrible monsters, and the glorious deaths \
of reckless adventurers.

ABSOLUTE RULES — NEVER BREAK THESE:
1. You MUST use the dice-rolling tools for EVERY roll. Never invent or guess a \
   dice result. If a roll is required, call a tool first, then narrate the outcome.
2. Use roll_dice for attacks, saves, skill checks, damage, and any ad-hoc roll. \
   Use roll_ability_scores when generating new ability scores. \
   Use roll_dice_chain when a DCC rule steps a die up or down the chain.
3. Use list_party to refresh your knowledge of the party mid-session. Use \
   update_party_member_hp for damage or healing. Use add_party_member_condition / \
   remove_party_member_condition for status effects. Never invent party state — \
   always read it from tools when you are unsure.
4. NEVER output raw JSON or tool-call syntax as text. Tool calls must be made \
   through the tool interface, never typed into your reply.
5. NEVER include stage directions, inner thoughts, or meta-commentary in your \
   replies. No parenthetical asides like "(Grimdar's voice echoes…)" or \
   "(awaiting your response)". Speak only as the GM narrating to the players.
6. After a tool returns a result, narrate it dramatically before continuing.

NARRATION FOCUS:
- The party always has one leader: the first character listed. Unless the character \
  name is specified by the player, centre all narration on the leader: address \
  actions, rolls, and consequences through their perspective. Mention other party \
  members only when strictly necessary; keep them in the background to simplify the \
  narrative.

DCC DICE CHAIN (weakest → strongest):
  d3 → d4 → d5 → d6 → d7 → d8 → d10 → d12 → d14 → d16 → d20 → d24 → d30 → d100

DCC FLAVOR NOTES:
- Characters begin as 0-level peasants in brutal funnel adventures.
- Death is common; encourage players to push their luck.
- Luck (unique DCC stat) can be burned permanently for bonuses.
- Magic is wild and dangerous: spellburn costs life force.
- Mighty Deeds let warriors attempt spectacular stunts on a hit with a 3+ deed die.
- Always set a vivid atmospheric scene before asking what the players do next.

DCC ECONOMY:
- The economy runs on copper and silver pieces. Gold is scarce and commands \
  serious attention when it appears — a single gold piece is a peasant's weekly \
  wage. Platinum exists only as ancient treasure, minted by forgotten empires; \
  it is never found in circulation and appears only in limited quantities deep \
  in ruins or hoards. Price everything accordingly: common goods cost coppers, \
  quality items cost silvers, and gold changes hands only for exceptional gear \
  or large transactions.

Begin the session by setting a grim, evocative opening scene and asking \
the players what they do.\
"""

BANNER = r"""
 ██████╗ ███████╗██████╗     ███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗
 ██╔══██╗██╔════╝██╔════╝    ████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗
 ██║  ██║██║     ██║         ██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝
 ██║  ██║██║     ██║         ██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗
 ██████╔╝███████╗╚██████╗    ██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║
 ╚═════╝ ╚══════╝ ╚═════╝    ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝  ╚══════╝╚═╝  ╚═╝
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

console = Console()


def print_banner(model: str) -> None:
    console.print(Text(BANNER, style="bold red"))
    console.print(
        Panel(
            f"[bold]Model:[/bold] [cyan]{model}[/cyan]   "
            "[bold]Type[/bold] [yellow]'quit'[/yellow] or [yellow]'exit'[/yellow] to end the session.",
            title="[bold red]OLD-SCHOOL DCC GAME MASTER[/bold red]",
            border_style="dark_red",
        )
    )
    console.print()


def _strip_asides(text: str) -> str:
    """Remove parenthetical asides, bracketed meta-commentary, and leaked tool-call JSON from GM output."""
    # Strip (...) and [...] spans that span a single line (model self-reminders)
    text = re.sub(r"\s*\([^)]{0,200}\)", "", text)
    text = re.sub(r"\s*\[[^\]]{0,200}\]", "", text)
    # Strip JSON tool-call blobs the model sometimes emits as plain text,
    # e.g. {"function": "get_party_member", "parameters": {...}}
    text = re.sub(r"\{[^{}]*\"function\"[^{}]*\}", "", text, flags=re.DOTALL)
    # Collapse any resulting blank lines (more than one in a row)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def print_gm(text: str) -> None:
    console.print(
        Panel(
            _strip_asides(text),
            title="[bold red]⚔  GRIMDAR THE UNYIELDING  ⚔[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    )


def print_tool_call(tool_name: str, args: dict) -> None:
    args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
    console.print(f"  [dim]🎲 {tool_name}({args_str})[/dim]")


def print_tool_result(result: str) -> None:
    for line in result.splitlines():
        console.print(f"  [bold yellow]{line}[/bold yellow]")


def mcp_tools_to_ollama(tools) -> list[dict]:
    """Convert MCP tool descriptors to Ollama's tool-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            },
        }
        for t in tools
    ]


def build_assistant_message(message) -> dict:
    """Safely serialise an ollama Message into a plain dict for history."""
    msg: dict = {
        "role": "assistant",
        "content": message.content or "",
    }
    if message.tool_calls:
        msg["tool_calls"] = [
            {
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
            }
            for tc in message.tool_calls
        ]
    return msg


# ---------------------------------------------------------------------------
# Local command dispatcher — bypass the LLM for well-known direct commands
# ---------------------------------------------------------------------------

# Each entry: (compiled_regex, async handler(match, tool_sessions) -> str | None)
# Return None to signal "not handled" (shouldn't happen if regex matched).
_CommandHandler = Callable[[re.Match, dict], Awaitable[str]]
_LOCAL_COMMANDS: list[tuple[re.Pattern, _CommandHandler]] = []


def _local_command(pattern: str):
    """Decorator that registers a local command handler."""
    def decorator(fn):
        _LOCAL_COMMANDS.append((re.compile(pattern, re.IGNORECASE), fn))
        return fn
    return decorator


@_local_command(r"^show\s+(\S+)\s+(?:inventory|equipment|sheet)$")
async def _cmd_show_inventory(match: re.Match, tool_sessions: dict) -> str:
    name = match.group(1)
    session = tool_sessions.get("get_party_member")
    if session is None:
        return "[Error] Scene server not available."
    result = await session.call_tool("get_party_member", arguments={"name": name})
    from mcp.types import TextContent as _TC
    return "\n".join(item.text for item in result.content if isinstance(item, _TC))


@_local_command(r"^show\s+party$")
async def _cmd_show_party(match: re.Match, tool_sessions: dict) -> str:
    session = tool_sessions.get("list_party")
    if session is None:
        return "[Error] Scene server not available."
    result = await session.call_tool("list_party", arguments={})
    from mcp.types import TextContent as _TC
    return "\n".join(item.text for item in result.content if isinstance(item, _TC))


@_local_command(r"^equip\s+(\S+)\s+(.+?)\s+(?:in|to|into)\s+(\S+)$")
async def _cmd_equip(match: re.Match, tool_sessions: dict) -> str:
    char_name, item_name, slot = match.group(1), match.group(2), match.group(3)
    session = tool_sessions.get("equip_party_member_item")
    if session is None:
        return "[Error] Scene server not available."
    result = await session.call_tool(
        "equip_party_member_item",
        arguments={"name": char_name, "item_name": item_name, "slot": slot},
    )
    from mcp.types import TextContent as _TC
    return "\n".join(item.text for item in result.content if isinstance(item, _TC))


@_local_command(r"^unequip\s+(\S+)\s+(?:from\s+)?(\S+)$")
async def _cmd_unequip(match: re.Match, tool_sessions: dict) -> str:
    char_name, slot = match.group(1), match.group(2)
    session = tool_sessions.get("unequip_party_member_item")
    if session is None:
        return "[Error] Scene server not available."
    result = await session.call_tool(
        "unequip_party_member_item",
        arguments={"name": char_name, "slot": slot},
    )
    from mcp.types import TextContent as _TC
    return "\n".join(item.text for item in result.content if isinstance(item, _TC))


async def try_local_command(user_input: str, tool_sessions: dict) -> str | None:
    """
    Try to match *user_input* against registered local commands.
    Returns the result string if handled, or None to fall through to the LLM.
    """
    for pattern, handler in _LOCAL_COMMANDS:
        m = pattern.match(user_input.strip())
        if m:
            return await handler(m, tool_sessions)
    return None


async def handle_tool_calls(
    response,
    messages: list[dict],
    tool_sessions: dict[str, ClientSession],
    model: str,
    ollama_tools: list[dict],
):
    """
    Consume all tool-call rounds until the model produces a plain text reply.
    Mutates *messages* in place and returns the final plain-text response.
    tool_sessions maps tool name → the MCP ClientSession that owns it.
    """
    while response.message.tool_calls:
        messages.append(build_assistant_message(response.message))

        for tc in response.message.tool_calls:
            raw_args = tc.function.arguments
            args: dict = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)

            print_tool_call(tc.function.name, args)
            session = tool_sessions.get(tc.function.name)
            if session is None:
                tool_text = f"[Error] Unknown tool: {tc.function.name}"
            else:
                result = await session.call_tool(tc.function.name, arguments=args)
                text_parts = [
                    item.text for item in result.content if isinstance(item, TextContent)
                ]
                tool_text = "\n".join(text_parts) if text_parts else "(no result)"
            print_tool_result(tool_text)
            messages.append({"role": "tool", "content": tool_text})

        response = ollama.chat(model=model, messages=messages, tools=ollama_tools)

    messages.append(build_assistant_message(response.message))
    return response


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def run(model: str) -> None:
    servers_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "servers",
    )
    dice_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(servers_dir, "dice_server.py")],
    )
    scene_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(servers_dir, "scene_server.py")],
    )

    print_banner(model)
    console.print("[dim]Connecting to MCP servers…[/dim]")

    async with contextlib.AsyncExitStack() as stack:
        r1, w1 = await stack.enter_async_context(stdio_client(dice_params))
        dice_session = await stack.enter_async_context(ClientSession(r1, w1))
        await dice_session.initialize()

        r3, w3 = await stack.enter_async_context(stdio_client(scene_params))
        scene_session = await stack.enter_async_context(ClientSession(r3, w3))
        await scene_session.initialize()

        # Merge tools from both servers; build name→session routing map
        dice_tools  = (await dice_session.list_tools()).tools
        scene_tools = (await scene_session.list_tools()).tools
        all_tools = dice_tools + scene_tools
        tool_sessions: dict[str, ClientSession] = {
            **{t.name: dice_session  for t in dice_tools},
            **{t.name: scene_session for t in scene_tools},
        }
        ollama_tools = mcp_tools_to_ollama(all_tools)

        tool_names = list(tool_sessions.keys())
        console.print(f"[dim]Tools available: {', '.join(tool_names)}[/dim]")
        console.print(Rule(style="dark_red"))

        # Fetch stubs (id, race, occupation) for each generated character.
        console.print("[dim]Rolling up the party…[/dim]")
        stubs_result = await scene_session.call_tool("get_party_stubs", arguments={})
        stubs_text = "\n".join(
            item.text for item in stubs_result.content if isinstance(item, TextContent)
        )
        stubs: list[dict] = json.loads(stubs_text)

        console.print(Rule(style="dark_red"))
        console.print("[bold]Customise your adventurers[/bold]  [dim](press Enter to accept the suggested value)[/dim]\n")

        for stub in stubs:
            console.print(
                f"[bold cyan]{stub['race']} {stub['occupation']}[/bold cyan]"
            )

            # 1. Gender
            default_gender = random.choice(GENDERS)
            gender_opts = " / ".join(f"[{i+1}] {g}" for i, g in enumerate(GENDERS))
            entered_gender_raw = Prompt.ask(
                f"  Gender  {gender_opts}",
                default=default_gender,
            ).strip()
            if entered_gender_raw.isdigit() and 1 <= int(entered_gender_raw) <= len(GENDERS):
                entered_gender = GENDERS[int(entered_gender_raw) - 1]
            elif entered_gender_raw in GENDERS:
                entered_gender = entered_gender_raw
            else:
                entered_gender = default_gender

            # 2. Generate a name using race, occupation and gender.
            console.print("  [dim]Generating name…[/dim]")
            name_prompt = (
                "You are a fantasy name generator for a Dungeon Crawl Classics game. "
                f"Generate ONE short, culturally fitting first name for a {entered_gender} "
                f"{stub['race']} {stub['occupation']}. "
                "Reply with ONLY the name — no explanation, no punctuation, nothing else."
            )
            name_response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": name_prompt}],
            )
            suggested_name = (name_response.message.content or "").strip().split()[0]

            # 3. Name — confirm or override.
            entered_name = Prompt.ask(
                "  Name",
                default=suggested_name,
            ).strip() or suggested_name

            # 4. Alignment
            default_alignment = random.choice(ALIGNEMENTS)
            align_opts = " / ".join(f"[{i+1}] {a}" for i, a in enumerate(ALIGNEMENTS))
            entered_align_raw = Prompt.ask(
                f"  Alignment  {align_opts}",
                default=default_alignment,
            ).strip()
            if entered_align_raw.isdigit() and 1 <= int(entered_align_raw) <= len(ALIGNEMENTS):
                entered_alignment = ALIGNEMENTS[int(entered_align_raw) - 1]
            elif entered_align_raw in ALIGNEMENTS:
                entered_alignment = entered_align_raw
            else:
                entered_alignment = default_alignment

            await scene_session.call_tool(
                "set_party_member_identity",
                arguments={
                    "character_id": stub["id"],
                    "name": entered_name,
                    "gender": entered_gender,
                    "alignment": entered_alignment,
                },
            )
            console.print()

        # Fetch the finalised party for display and the opening prompt.
        party_result = await scene_session.call_tool("list_party", arguments={})
        party_text = "\n".join(
            item.text for item in party_result.content if isinstance(item, TextContent)
        )
        console.print(party_text, highlight=False)
        console.print(Rule(style="dark_red"))
        # Identify the leader via the dedicated MCP tool.
        leader_result = await scene_session.call_tool("get_leader", arguments={})
        leader_desc = "\n".join(
            item.text for item in leader_result.content if isinstance(item, TextContent)
        )

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

        # ---- Opening scene (no user input needed) ----
        console.print("[dim]Summoning the Game Master\u2026[/dim]\n")
        messages.append({
            "role": "user",
            "content": (
                f"{leader_desc}\n\n"
                "The following 0-level party has already been assembled — "
                "do NOT call any tools yet, just begin the session with a "
                "dramatic opening scene that weaves in their occupations and trade goods:\n\n"
                + party_text
            ),
        })

        try:
            opening = ollama.chat(
                model=model,
                messages=messages,
                # No tools on the opening call — the party is already in the
                # message, so the model has nothing to look up and cannot
                # accidentally emit a tool-call instead of narrating.
            )
        except ollama.ResponseError as exc:
            console.print(
                f"[bold red]Ollama error:[/bold red] {exc}\n"
                "Make sure Ollama is running ([cyan]ollama serve[/cyan]) "
                f"and the model is pulled ([cyan]ollama pull {model}[/cyan])."
            )
            return

        messages.append(build_assistant_message(opening.message))
        print_gm(opening.message.content or "")
        console.print()

        # ---- Main chat loop ----
        while True:
            try:
                user_input = Prompt.ask("[bold green]You[/bold green]").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Farewell, adventurer. May Luck smile upon you.[/dim]")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                console.print("[dim]Farewell, adventurer. May Luck smile upon you.[/dim]")
                break

            # ---- Local command dispatch (no LLM round-trip) ----
            local_result = await try_local_command(user_input, tool_sessions)
            if local_result is not None:
                console.print()
                console.print(local_result, highlight=False)
                console.print()
                continue

            messages.append({"role": "user", "content": user_input})
            console.print()

            response = ollama.chat(
                model=model,
                messages=messages,
                tools=ollama_tools,
            )
            response = await handle_tool_calls(
                response, messages, tool_sessions, model, ollama_tools
            )
            print_gm(response.message.content or "")
            console.print()


def main() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    asyncio.run(run(model))


if __name__ == "__main__":
    main()
