# ai_sdlc/commands/status.py
"""`aisdlc status` – show progress through lifecycle steps."""

from ai_sdlc.types import ConfigDict, LockDict
from ai_sdlc.utils import load_config, read_lock


def run_status(args: list[str] | None = None) -> None:
    """Show progress through lifecycle steps.

    Args:
        args: Command line arguments (currently unused)
    """
    conf: ConfigDict = load_config()
    steps = conf["steps"]
    lock: LockDict = read_lock()
    print("Active workstreams\n------------------")
    if not lock:
        print("none – create one with `aisdlc new`")
        return
    if "slug" not in lock or "current" not in lock:
        print("none – invalid lock file, create one with `aisdlc new`")
        return
    slug = lock["slug"]
    cur = lock["current"]
    idx = steps.index(cur)
    bar = " ▸ ".join([("✅" if i <= idx else "☐") + s[2:] for i, s in enumerate(steps)])
    print(f"{slug:20} {cur:12} {bar}")
