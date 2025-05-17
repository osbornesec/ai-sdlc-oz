#!/usr/bin/env python
"""Entry-point for the `aisdlc` CLI."""

from __future__ import annotations

import sys
from importlib import import_module
from typing import Callable, Dict

_COMMANDS: Dict[str, str] = {
    "init": "ai_sdlc.commands.init:run_init",
    "new": "ai_sdlc.commands.new:run_new",
    "next": "ai_sdlc.commands.next:run_next",
    "status": "ai_sdlc.commands.status:run_status",
    "done": "ai_sdlc.commands.done:run_done",
}


def _resolve(dotted: str) -> Callable[..., None]:
    """Import `"module:function"` and return the function object."""
    module_name, func_name = dotted.split(":")
    module = import_module(module_name)
    return getattr(module, func_name)


def main() -> None:  # noqa: D401
    """Run the requested sub-command."""
    cmd, *args = sys.argv[1:] or ["--help"]
    if cmd not in _COMMANDS:
        valid = "|".join(_COMMANDS.keys())
        print(f"Usage: aisdlc [{valid}]")
        sys.exit(1)

    handler = _resolve(_COMMANDS[cmd])
    handler(args) if args else handler()


if __name__ == "__main__":
    main()
