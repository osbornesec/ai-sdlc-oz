# ai_sdlc/commands/next.py
from pathlib import Path
import tomllib, subprocess, re, json

ROOT = Path(__file__).resolve().parents[2]

def run_next():
    conf = tomllib.loads((ROOT / ".aisdlc").read_text())
    steps = conf["steps"]

    # read lock or start fresh
    lock_path = ROOT / ".aisdlc.lock"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    slug   = lock["slug"]
    idx    = steps.index(lock["current"]) if lock else 0

    if idx + 1 >= len(steps):
        print("🎉  All steps done. Run `aisdlc done`.")
        return

    prev_step = steps[idx]
    next_step = steps[idx + 1]

    workdir   = ROOT / conf["active_dir"] / slug
    prev_file = workdir / f"{prev_step}-{slug}.md"

    if not prev_file.exists():
        print(f"❌  Expected {prev_file} not found.")
        return

    prompt_file = ROOT / conf["prompt_dir"] / f"{next_step}-prompt.md"

    idea_txt   = prev_file.read_text()
    prompt_txt = prompt_file.read_text()
    merged     = prompt_txt.replace("<prev_step></prev_step>", idea_txt)

    tmp = Path("/tmp/aisdlc_prompt.md")
    tmp.write_text(merged)

    out = subprocess.check_output(["cursor", "agent", "--file", str(tmp)])
    (workdir / f"{next_step}-{slug}.md").write_bytes(out)

    lock.update({"current": next_step})
    lock_path.write_text(json.dumps(lock, indent=2))
