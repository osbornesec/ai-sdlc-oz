"""`aisdlc done` – validate finished stream and archive it."""

import shutil
from pathlib import Path

from ai_sdlc.utils import ROOT, load_config, read_lock, write_lock

def run_done() -> None:
    conf  = load_config()
    steps = conf["steps"]
    lock  = read_lock()
    if not lock:
        print("❌  No active workstream.")
        return
    slug = lock["slug"]
    if lock["current"] != steps[-1]:
        print("❌  Workstream not finished yet. Complete all steps before archiving.")
        return
    workdir = ROOT / conf["active_dir"] / slug
    missing = [s for s in steps if not (workdir / f"{s}-{slug}.md").exists()]
    if missing:
        print("❌  Missing files:", ", ".join(missing))
        return
    dest = ROOT / conf["done_dir"] / slug
    shutil.move(str(workdir), dest)
    write_lock({})
    print(f"🎉  Archived to {dest}")
