"""
DCC Game Master — Command-Line Interface

An old-school Dungeon Crawl Classics game master powered by Ollama and the
DCC Dice Roller MCP server. The GM uses real dice rolls (never invented ones)
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
import sys

import ollama
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.types import TextContent
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.text import Text

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
   Use roll_ability_scores when setting up or rolling new characters. \
   Use roll_dice_chain when a DCC rule steps a die up or down the chain.
3. After a tool returns a result, narrate it dramatically before continuing.

DCC DICE CHAIN (weakest → strongest):
  d3 → d4 → d5 → d6 → d7 → d8 → d10 → d12 → d14 → d16 → d20 → d24 → d30 → d100

DCC FLAVOR NOTES:
- Characters begin as 0-level peasants in brutal funnel adventures.
- Death is common; encourage players to push their luck.
- Luck (unique DCC stat) can be burned permanently for bonuses.
- Magic is wild and dangerous: spellburn costs life force.
- Mighty Deeds let warriors attempt spectacular stunts on a hit with a 3+ deed die.
- Always set a vivid atmospheric scene before asking what the players do next.

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


def print_gm(text: str) -> None:
    console.print(
        Panel(
            text,
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
    char_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(servers_dir, "character_server.py")],
    )

    print_banner(model)
    console.print("[dim]Connecting to MCP servers…[/dim]")

    async with contextlib.AsyncExitStack() as stack:
        r1, w1 = await stack.enter_async_context(stdio_client(dice_params))
        dice_session = await stack.enter_async_context(ClientSession(r1, w1))
        await dice_session.initialize()

        r2, w2 = await stack.enter_async_context(stdio_client(char_params))
        char_session = await stack.enter_async_context(ClientSession(r2, w2))
        await char_session.initialize()

        # Merge tools from both servers; build name→session routing map
        dice_tools = (await dice_session.list_tools()).tools
        char_tools = (await char_session.list_tools()).tools
        all_tools = dice_tools + char_tools
        tool_sessions: dict[str, ClientSession] = {
            **{t.name: dice_session for t in dice_tools},
            **{t.name: char_session for t in char_tools},
        }
        ollama_tools = mcp_tools_to_ollama(all_tools)

        tool_names = list(tool_sessions.keys())
        console.print(f"[dim]Tools available: {', '.join(tool_names)}[/dim]")
        console.print(Rule(style="dark_red"))

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

        # ---- Opening scene (no user input needed) ----
        console.print("[dim]Summoning the Game Master…[/dim]\n")
        messages.append({"role": "user", "content": "Begin the session."})

        try:
            opening = ollama.chat(
                model=model,
                messages=messages,
                tools=ollama_tools,
            )
        except ollama.ResponseError as exc:
            console.print(
                f"[bold red]Ollama error:[/bold red] {exc}\n"
                "Make sure Ollama is running ([cyan]ollama serve[/cyan]) "
                f"and the model is pulled ([cyan]ollama pull {model}[/cyan])."
            )
            return

        opening = await handle_tool_calls(
            opening, messages, tool_sessions, model, ollama_tools
        )
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
