"""`aisdlc next` – generate the next lifecycle file via Cursor agent."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from ai_sdlc.utils import ROOT, load_config, read_lock, write_lock

# Define a reasonable timeout for cursor agent calls
CURSOR_AGENT_TIMEOUT = 300  # 5 minutes in seconds

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
        print(f"❌  Prompt file {prompt_file} missing.")
        return

    print(f"ℹ️  Reading previous step from: {prev_file}")
    prev_step_content = prev_file.read_text()
    print(f"ℹ️  Reading prompt template from: {prompt_file}")
    prompt_template_content = prompt_file.read_text()
    
    merged_prompt = prompt_template_content.replace(PLACEHOLDER, prev_step_content)
    tmp_prompt_path_str = None  # Initialize for finally block
    try:
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".md", encoding="utf-8") as tmp_file_obj:
            tmp_prompt_path_str = tmp_file_obj.name
            tmp_file_obj.write(merged_prompt)

        print(f"🧠  Calling Cursor agent for step {next_step} …")
        print(f"   Using temporary prompt file: {tmp_prompt_path_str}")
        try:
            output = subprocess.check_output(
                ["cursor", "agent", "--file", tmp_prompt_path_str],
                text=True,
                timeout=CURSOR_AGENT_TIMEOUT,
            )
    except subprocess.CalledProcessError as e:
        print(f"❌  Cursor agent failed with exit code {e.returncode}.")
        if e.stdout: print(f"Stdout:\n{e.stdout}")
        if e.stderr: print(f"Stderr:\n{e.stderr}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"❌  Cursor agent timed out after {CURSOR_AGENT_TIMEOUT} seconds.")
        sys.exit(1)
    finally:
        if tmp_prompt_path_str and Path(tmp_prompt_path_str).exists():
            Path(tmp_prompt_path_str).unlink()

    print(f"ℹ️  Cursor agent finished. Writing output to: {next_file}")
    try:
        next_file.write_text(output)
        lock["current"] = next_step
        write_lock(lock)
        print(f"✅  Wrote {next_file}")
    except OSError as e:
        print(f"❌  Error writing output to {next_file}: {e}")
        sys.exit(1)
