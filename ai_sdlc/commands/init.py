# ai_sdlc/commands/init.py
from pathlib import Path

def run_init():
    root = Path.cwd()
    (root / "doing").mkdir(exist_ok=True)
    (root / "done").mkdir(exist_ok=True)
    lock = root / ".aisdlc.lock"
    if not lock.exists():
        lock.write_text("{}")
    print("✅  AI-SDLC initialized.")
