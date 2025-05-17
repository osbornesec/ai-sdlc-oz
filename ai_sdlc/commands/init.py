"""`aisdlc init` – scaffold baseline folders & lock."""

from pathlib import Path

from ai_sdlc.utils import ROOT, write_lock


def run_init() -> None:
    """Create default folders and empty lock."""
    for folder in ("doing", "done"):
        (ROOT / folder).mkdir(exist_ok=True)

    write_lock({})
    print("✅  AI-SDLC initialized – ready for `aisdlc new \"Your idea\"`")
