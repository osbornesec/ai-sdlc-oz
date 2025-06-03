"""`aisdlc next` – generate the next lifecycle file via AI agent."""

from __future__ import annotations

import sys

from ai_sdlc.services.context7_service import Context7Service
from ai_sdlc.utils import ROOT, load_config, read_lock, write_lock

PLACEHOLDER = "<prev_step></prev_step>"


def run_next(args: list[str] = None) -> None:
    conf = load_config()
    steps = conf["steps"]
    lock = read_lock()

    if not lock:
        print("❌  No active workstream. Run `aisdlc new` first.")
        return

    slug = lock["slug"]
    idx = steps.index(lock["current"])
    if idx + 1 >= len(steps):
        print("🎉  All steps complete. Run `aisdlc done` to archive.")
        return

    prev_step = steps[idx]
    next_step = steps[idx + 1]

    workdir = ROOT / conf["active_dir"] / slug
    prev_file = workdir / f"{prev_step}-{slug}.md"
    prompt_file = ROOT / conf["prompt_dir"] / f"{next_step}.prompt.yml"
    next_file = workdir / f"{next_step}-{slug}.md"

    if not prev_file.exists():
        print(f"❌ Error: The previous step's output file '{prev_file}' is missing.")
        print(f"   This file is required as input to generate the '{next_step}' step.")
        print(
            "   Please restore this file (e.g., from version control) or ensure it was correctly generated."
        )
        print(
            f"   If you need to restart the '{prev_step}', you might need to adjust '.aisdlc.lock' or re-run the command that generates '{prev_step}'."
        )
        sys.exit(1)  # Make it a harder exit
    if not prompt_file.exists():
        print(f"❌ Critical Error: Prompt template file '{prompt_file}' is missing.")
        print(f"   This file is essential for generating the '{next_step}' step.")
        print(f"   Please ensure it exists in your '{conf['prompt_dir']}/' directory.")
        print(
            "   You may need to restore it from version control or your initial 'aisdlc init' setup."
        )
        sys.exit(1)  # Make it a harder exit

    print(f"ℹ️  Reading previous step from: {prev_file}")
    prev_step_content = prev_file.read_text()
    print(f"ℹ️  Reading prompt template from: {prompt_file}")
    prompt_template_content = prompt_file.read_text()

    merged_prompt = prompt_template_content.replace(PLACEHOLDER, prev_step_content)

    # Context7 Integration
    context7_enabled = conf.get("context7", {}).get("enabled", True)  # Default to enabled
    if context7_enabled:
        print("📚  Enriching prompt with Context7 documentation...")
        
        # Initialize Context7 service
        cache_dir = ROOT / ".context7_cache"
        context7 = Context7Service(cache_dir)
        
        # Read all previous content for better context
        all_content = []
        for i in range(idx + 1):
            step_file = workdir / f"{steps[i]}-{slug}.md"
            if step_file.exists():
                all_content.append(step_file.read_text())
        
        combined_content = "\n\n".join(all_content)
        
        # Enrich the prompt with library documentation
        merged_prompt = context7.enrich_prompt(
            merged_prompt,
            next_step,
            combined_content
        )
        
        # Show detected libraries
        detected_libs = context7.extract_libraries_from_text(combined_content)
        if detected_libs:
            print(f"   Detected libraries: {', '.join(detected_libs)}")

    # Create a prompt file for the user to use with their preferred AI tool
    prompt_output_file = workdir / f"_prompt-{next_step}.md"
    prompt_output_file.write_text(merged_prompt)

    print(f"📝  Generated AI prompt file: {prompt_output_file}")
    print(
        f"🤖  Please use this prompt with your preferred AI tool to generate content for step '{next_step}'"
    )
    print(f"    Then save the AI's response to: {next_file}")
    print()
    print("💡  Options:")
    print(
        "    • Copy the prompt content and paste into any AI chat (Claude, ChatGPT, etc.)"
    )
    print("    • Use with Cursor: cursor agent --file " + str(prompt_output_file))
    print("    • Use with any other AI-powered editor or CLI tool")
    print()
    print(
        f"⏭️   After saving the AI response, the next step file should be: {next_file}"
    )
    print("    Once ready, run 'aisdlc next' again to continue to the next step.")

    # Check if the user has already created the next step file
    if next_file.exists():
        print(f"✅  Found existing file: {next_file}")
        print("    Proceeding to update the workflow state...")

        # Update the lock to reflect the current step
        lock["current"] = next_step
        write_lock(lock)
        print(f"✅  Advanced to step: {next_step}")

        # Clean up the prompt file since it's no longer needed
        if prompt_output_file.exists():
            prompt_output_file.unlink()
            print(f"🧹  Cleaned up prompt file: {prompt_output_file}")

        return
    else:
        print(f"⏸️   Waiting for you to create: {next_file}")
        print(
            "    Use the generated prompt with your AI tool, then run 'aisdlc next' again."
        )
        return
