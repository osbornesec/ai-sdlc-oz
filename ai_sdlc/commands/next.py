"""`aisdlc next` – generate the next lifecycle file via AI agent."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from ai_sdlc.utils import ROOT, load_config, read_lock, write_lock

# Define a reasonable timeout for AI agent calls
AI_AGENT_TIMEOUT = 45  # 45 seconds

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
        print(f"❌ Error: The previous step's output file '{prev_file}' is missing.")
        print(f"   This file is required as input to generate the '{next_step}' step.")
        print("   Please restore this file (e.g., from version control) or ensure it was correctly generated.")
        print(f"   If you need to restart the '{prev_step}', you might need to adjust '.aisdlc.lock' or re-run the command that generates '{prev_step}'.")
        sys.exit(1)  # Make it a harder exit
    if not prompt_file.exists():
        print(f"❌ Critical Error: Prompt template file '{prompt_file}' is missing.")
        print(f"   This file is essential for generating the '{next_step}' step.")
        print(f"   Please ensure it exists in your '{conf['prompt_dir']}/' directory.")
        print("   You may need to restore it from version control or your initial 'aisdlc init' setup.")
        sys.exit(1) # Make it a harder exit

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

        print(f"🧠  Calling AI agent for step {next_step} …")
        print(f"   Using temporary prompt file: {tmp_prompt_path_str}")
        try:
            output = subprocess.check_output(
                ["cursor", "agent", "--file", tmp_prompt_path_str],
                text=True,
                timeout=AI_AGENT_TIMEOUT,
            )
        except subprocess.CalledProcessError as e:
            print(f"❌  AI agent failed with exit code {e.returncode}.")
            if e.stdout:
                print(f"Stdout:\n{e.stdout}")
            if e.stderr:
                print(f"Stderr:\n{e.stderr}")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print(f"❌  AI agent timed out after {AI_AGENT_TIMEOUT} seconds.")
            sys.exit(1)
    finally:
        if tmp_prompt_path_str and Path(tmp_prompt_path_str).exists():
            Path(tmp_prompt_path_str).unlink()

    print(f"ℹ️  AI agent finished. Writing output to: {next_file}")
    try:
        next_file.write_text(output)
        lock["current"] = next_step
        write_lock(lock)
        print(f"✅  Wrote {next_file}")
    except OSError as e:
        print(f"❌  Error writing output to {next_file}: {e}")
        sys.exit(1)
