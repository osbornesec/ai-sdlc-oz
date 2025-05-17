"""`aisdlc next` – generate the next lifecycle file via Cursor agent."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ai_sdlc.utils import ROOT, load_config, read_lock, write_lock

PLACEHOLDER = "<prev_step></prev_step>"

def run_next() -> None:
    conf = load_config()
    steps = conf["steps"]
    lock = read_lock()

    if not lock:
        print("❌  No active workstream. Run `aisdlc new` first.")
        return

    slug = lock["slug"]
    idx  = steps.index(lock["current"])
    if idx + 1 >= len(steps):
        print("🎉  All steps complete. Run `aisdlc done` to archive.")
        return

    prev_step = steps[idx]
    next_step = steps[idx + 1]

    workdir = ROOT / conf["active_dir"] / slug
    prev_file   = workdir / f"{prev_step}-{slug}.md"
    prompt_file = ROOT / conf["prompt_dir"] / f"{next_step}-prompt.md"
    next_file   = workdir / f"{next_step}-{slug}.md"

    if not prev_file.exists():
        print(f"❌  Expected file {prev_file} not found.")
        return
    if not prompt_file.exists():
        print(f"❌  Prompt {prompt_file} missing.")
        return

    merged_prompt = prompt_file.read_text().replace(PLACEHOLDER, prev_file.read_text())
    tmp_prompt = Path("/tmp/aisdlc_prompt.md")
    tmp_prompt.write_text(merged_prompt)

    print(f"🧠  Calling Cursor agent for step {next_step} …")
    try:
        output = subprocess.check_output(
            ["cursor", "agent", "--file", str(tmp_prompt)],
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print("❌  Cursor agent failed:", e)
        sys.exit(1)

    next_file.write_text(output)
    lock["current"] = next_step
    write_lock(lock)
    print(f"✅  Wrote {next_file}")
