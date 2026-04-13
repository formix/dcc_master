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
    format_sheet as _fmt_sheet,
)

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


if __name__ == "__main__":
    mcp.run()
