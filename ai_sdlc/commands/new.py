"""`aisdlc new` – start a work-stream from an idea title."""

from __future__ import annotations

import datetime
import sys

from ai_sdlc.utils import ROOT, load_config, slugify, write_lock


def run_new(args: list[str] | None) -> None:
    """Create the work-stream folder and first markdown file.

    Args:
        args: Command line arguments containing the idea title

    Raises:
        SystemExit: If arguments are invalid or filesystem operations fail
    """
    if not args:
        print('Usage: aisdlc new "Idea title"')
        sys.exit(1)

    # Load configuration to get the first step
    config = load_config()
    first_step = config["steps"][0]

    idea_text = " ".join(args)

    # Validate input length
    if len(idea_text) > 200:
        print("❌  Error: Idea title too long (max 200 characters)")
        sys.exit(1)

    if len(idea_text) < 3:
        print("❌  Error: Idea title too short (min 3 characters)")
        sys.exit(1)

    try:
        slug = slugify(idea_text)
    except ValueError as e:
        print(f"❌  Error: {e}")
        print("   Idea title must contain alphanumeric characters")
        sys.exit(1)

    workdir = ROOT / config["active_dir"] / slug

    # Validate path to prevent traversal
    try:
        workdir_resolved = workdir.resolve()
        expected_parent = (ROOT / config["active_dir"]).resolve()
        if not str(workdir_resolved).startswith(str(expected_parent)):
            print("❌  Security Error: Invalid path detected")
            sys.exit(1)
    except Exception as e:
        print(f"❌  Error validating path: {e}")
        sys.exit(1)

    if workdir.exists():
        print(f"❌  Work-stream '{slug}' already exists.")
        sys.exit(1)

    try:
        workdir.mkdir(parents=True)
        idea_file = workdir / f"{first_step}-{slug}.md"
        idea_file.write_text(
            f"# {idea_text}\n\n## Problem\n\n## Solution\n\n## Rabbit Holes\n",
        )

        write_lock(
            {
                "slug": slug,
                "current": first_step,
                "created": datetime.datetime.utcnow().isoformat(),
            },
        )
        print(f"✅  Created {idea_file}.  Fill it out, then run `aisdlc next`.")
    except OSError as e:
        print(f"❌  Error creating work-stream files for '{slug}': {e}")
        sys.exit(1)
