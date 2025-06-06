#!/usr/bin/env python
"""Entry-point for the `aisdlc` CLI."""

from __future__ import annotations

import sys
from collections.abc import Callable

from .commands import context, done, init, new, next, status
from .utils import load_config, read_lock  # Added for status display

_COMMANDS: dict[str, Callable[[list[str]], None]] = {
    "init": init.run_init,
    "new": new.run_new,
    "next": next.run_next,
    "status": status.run_status,
    "done": done.run_done,
    "context": context.run_context,
}


def _display_compact_status() -> None:
    """Displays a compact version of the current workstream status."""
    lock = read_lock()
    if not lock or "slug" not in lock:
        return  # No active workstream or invalid lock

    try:
        conf = load_config()
        steps = conf["steps"]
        slug = lock.get("slug", "N/A")
        current_step_name = lock.get("current", "N/A")

        if current_step_name in steps:
            idx = steps.index(current_step_name)
            # Steps are in format like "01-idea", take the part after the dash
            bar = " ▸ ".join(
                [
                    ("✅" if i <= idx else "☐") + s.split("-", 1)[1]
                    for i, s in enumerate(steps)
                ]
            )
            print(f"\n---\n📌 Current: {slug} @ {current_step_name}\n   {bar}\n---")
        else:
            print(
                f"\n---\n📌 Current: {slug} @ {current_step_name} (Step not in config)\n---"
            )
    except FileNotFoundError:  # .aisdlc missing
        print(
            "\n---\n📌 AI-SDLC config (.aisdlc) not found. Cannot display status.\n---"
        )
    except Exception:  # Catch other potential errors during status display
        print(
            "\n---\n📌 Could not display current status due to an unexpected issue.\n---"
        )


def main() -> None:  # noqa: D401
    """Run the requested sub-command."""
    cmd, *args = sys.argv[1:] or ["--help"]
    if cmd not in _COMMANDS:
        valid = "|".join(_COMMANDS.keys())
        print(f"Usage: aisdlc [{valid}] [--help]")
        sys.exit(1)

    handler = _COMMANDS[cmd]
    handler(args)

    # Display status after most commands, unless it's status itself or init (before lock exists)
    if cmd not in ["status", "init"]:
        _display_compact_status()


if __name__ == "__main__":
    main()
