"""`aisdlc done` – validate finished stream and archive it."""

import shutil
import sys

from ai_sdlc.types import ConfigDict, LockDict
from ai_sdlc.utils import ROOT, load_config, read_lock, write_lock


def run_done(args: list[str] | None = None) -> None:
    """Archive the current workstream to done/ and reset the lock.

    Args:
        args: Command line arguments (currently unused)

    Raises:
        SystemExit: If filesystem operations fail
    """
    conf: ConfigDict = load_config()
    steps = conf["steps"]
    lock: LockDict = read_lock()
    if not lock:
        print("❌  No active workstream.")
        sys.exit(1)
    if "slug" not in lock or "current" not in lock:
        print("❌  Invalid lock file. Run 'aisdlc status' to regenerate.")
        sys.exit(1)
    slug = lock["slug"]
    if lock["current"] != steps[-1]:
        print("❌  Workstream not finished yet. Complete all steps before archiving.")
        sys.exit(1)
    workdir = ROOT / conf["active_dir"] / slug
    missing = [s for s in steps if not (workdir / f"{s}-{slug}.md").exists()]
    if missing:
        print("❌  Missing files:", ", ".join(missing))
        sys.exit(1)
    dest = ROOT / conf["done_dir"] / slug
    try:
        shutil.move(str(workdir), dest)
        write_lock({})
        print(f"🎉  Archived to {dest}")
    except OSError as e:
        print(f"❌  Error archiving work-stream '{slug}': {e}")
        sys.exit(1)
