"""`aisdlc next` – generate the next lifecycle file via AI agent."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from ai_sdlc.services.ai_service import (
    AiServiceError,
    ApiKeyMissingError,
    OpenAIError,
    UnsupportedProviderError,
    generate_text,
)
from ai_sdlc.services.context7_service import Context7Service
from ai_sdlc.types import ConfigDict, LockDict
from ai_sdlc.utils import ROOT, load_config, read_lock, write_lock

PLACEHOLDER = "<prev_step></prev_step>"


def _validate_required_files(
    prev_file: Path,
    prompt_file: Path,
    prev_step: str,
    next_step: str,
    conf: ConfigDict,
) -> None:
    """Validate that required files exist."""
    if not prev_file.exists():
        print(f"❌ Error: The previous step's output file '{prev_file}' is missing.")
        print(f"   This file is required as input to generate the '{next_step}' step.")
        print(
            "   Please restore this file (e.g., from version control) or ensure it was correctly generated."
        )
        print(
            f"   If you need to restart the '{prev_step}', you might need to adjust '.aisdlc.lock' or re-run the command that generates '{prev_step}'."
        )
        sys.exit(1)

    if not prompt_file.exists():
        print(f"❌ Critical Error: Prompt template file '{prompt_file}' is missing.")
        print(f"   This file is essential for generating the '{next_step}' step.")
        print(f"   Please ensure it exists in your '{conf['prompt_dir']}/' directory.")
        print(
            "   You may need to restore it from version control or your initial 'aisdlc init' setup."
        )
        sys.exit(1)


def _read_and_merge_content(prev_file: Path, prompt_file: Path) -> str:
    """Read previous step and prompt template, then merge them."""
    print(f"ℹ️  Reading previous step from: {prev_file}")
    prev_step_content = prev_file.read_text()
    print(f"ℹ️  Reading prompt template from: {prompt_file}")
    prompt_template_content = prompt_file.read_text()
    return prompt_template_content.replace(PLACEHOLDER, prev_step_content)


@dataclass
class Context7Config:
    """Configuration for Context7 enrichment."""

    conf: ConfigDict
    workdir: Path
    steps: list[str]
    idx: int
    slug: str
    next_step: str


def _apply_context7_enrichment(config: Context7Config, merged_prompt: str) -> str:
    """Apply Context7 enrichment if enabled."""
    context7_cfg = config.conf.get("context7")
    context7_enabled = (
        True if context7_cfg is None else context7_cfg.get("enabled", True)
    )
    if not context7_enabled:
        return merged_prompt

    print("📚  Enriching prompt with Context7 documentation...")

    # Initialize Context7 service
    context7 = Context7Service(ROOT / ".context7_cache")

    # Read all previous content for better context
    all_content = []
    for i in range(config.idx + 1):
        step_file = config.workdir / f"{config.steps[i]}-{config.slug}.md"
        if step_file.exists():
            all_content.append(step_file.read_text())

    combined_content = "\n\n".join(all_content)

    # Enrich the prompt with library documentation
    enriched_prompt = context7.enrich_prompt(
        merged_prompt, config.next_step, combined_content
    )

    # Show detected libraries
    detected_libs = context7.extract_libraries_from_text(combined_content)
    if detected_libs:
        print(f"   Detected libraries: {', '.join(detected_libs)}")

    return enriched_prompt


def _write_prompt_and_show_instructions(
    prompt_output_file: Path, merged_prompt: str, next_step: str, next_file: Path
) -> None:
    """Write prompt file and display instructions."""
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


def _handle_next_step_file(
    next_file: Path, next_step: str, lock: LockDict, prompt_output_file: Path
) -> None:
    """Check if next step file exists and handle accordingly."""
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
    else:
        print(f"⏸️   Waiting for you to create: {next_file}")
        print(
            "    Use the generated prompt with your AI tool, then run 'aisdlc next' again."
        )


def _validate_workflow_state(
    conf: ConfigDict, lock: LockDict
) -> tuple[str, int, list[str]]:
    """Validate workflow state and return slug, current index, and steps."""
    if not lock:
        print("❌  No active workstream. Run `aisdlc new` first.")
        sys.exit(1)

    if "slug" not in lock or "current" not in lock:
        print("❌  Invalid lock file. Run 'aisdlc status' to regenerate.")
        sys.exit(1)

    slug = lock["slug"]
    steps = conf["steps"]
    idx = steps.index(lock["current"])

    if idx + 1 >= len(steps):
        print("🎉  All steps complete. Run `aisdlc done` to archive.")
        sys.exit(0)

    return slug, idx, steps


def _prepare_file_paths(
    conf: ConfigDict, slug: str, prev_step: str, next_step: str
) -> tuple[Path, Path, Path, Path, Path]:
    """Prepare and return all required file paths."""
    workdir = ROOT / conf["active_dir"] / slug
    prev_file = workdir / f"{prev_step}-{slug}.md"
    prompt_file = ROOT / conf["prompt_dir"] / f"{next_step}.prompt.yml"
    next_file = workdir / f"{next_step}-{slug}.md"
    prompt_output_file = workdir / f"_prompt-{next_step}.md"

    return workdir, prev_file, prompt_file, next_file, prompt_output_file


def run_next(args: list[str] | None = None) -> None:
    """Generate the next lifecycle file via AI agent.

    Args:
        args: Command line arguments (currently unused)

    Raises:
        SystemExit: If no active workstream, all steps complete, or file errors occur
    """
    conf: ConfigDict = load_config()
    lock: LockDict = read_lock()

    # Validate workflow state
    slug, idx, steps = _validate_workflow_state(conf, lock)

    prev_step = steps[idx]
    next_step = steps[idx + 1]

    # Prepare file paths
    workdir, prev_file, prompt_file, next_file, prompt_output_file = (
        _prepare_file_paths(conf, slug, prev_step, next_step)
    )

    # Validate required files
    _validate_required_files(prev_file, prompt_file, prev_step, next_step, conf)

    # Read and merge content
    merged_prompt = _read_and_merge_content(prev_file, prompt_file)

    # Apply Context7 enrichment if enabled
    context7_config = Context7Config(
        conf=conf, workdir=workdir, steps=steps, idx=idx, slug=slug, next_step=next_step
    )
    merged_prompt = _apply_context7_enrichment(context7_config, merged_prompt)

    ai_provider_config = conf.get("ai_provider")
    perform_api_call = False # Flag to determine if API call should be attempted

    if ai_provider_config:
        direct_api_calls_enabled = ai_provider_config.get("direct_api_calls", False)
        provider_name = ai_provider_config.get("name", "manual")
        if direct_api_calls_enabled and provider_name != "manual":
            perform_api_call = True

    if perform_api_call and ai_provider_config: # ai_provider_config should exist if perform_api_call is True
        print(f"🤖 Attempting to generate text using AI provider: {ai_provider_config.get('name')}...")
        try:
            generated_content = generate_text(merged_prompt, ai_provider_config)
            next_file.write_text(generated_content)
            print(f"✅ AI successfully generated content and saved to: {next_file}")
            # Successfully generated, so we can skip writing the prompt file for manual use
            if prompt_output_file.exists(): # Clean up _prompt- file if it was somehow created before or in a previous failed run
                prompt_output_file.unlink()

        except ApiKeyMissingError as e:
            print(f"❌ API Key Missing Error: {e}")
            print("   Falling back to manual prompt generation.")
            _write_prompt_and_show_instructions(prompt_output_file, merged_prompt, next_step, next_file)
        except UnsupportedProviderError as e:
            print(f"❌ Unsupported Provider Error: {e}")
            print("   Falling back to manual prompt generation.")
            _write_prompt_and_show_instructions(prompt_output_file, merged_prompt, next_step, next_file)
        except OpenAIError as e: # Specific OpenAI errors
            print(f"❌ OpenAI API Error: {e}")
            print("   Falling back to manual prompt generation.")
            _write_prompt_and_show_instructions(prompt_output_file, merged_prompt, next_step, next_file)
        except AiServiceError as e: # Catch-all for other AiService errors
            print(f"❌ AI Service Error: {e}")
            print("   Falling back to manual prompt generation.")
            _write_prompt_and_show_instructions(prompt_output_file, merged_prompt, next_step, next_file)
        except Exception as e: # Catch unexpected errors during API call
            print(f"❌ An unexpected error occurred during AI text generation: {e}")
            print("   Falling back to manual prompt generation.")
            _write_prompt_and_show_instructions(prompt_output_file, merged_prompt, next_step, next_file)
    else:
        if ai_provider_config and ai_provider_config.get("name") != "manual":
            print("ℹ️  Direct API calls are disabled or provider is not configured for direct calls.")
        # Write prompt and display instructions for manual processing
        _write_prompt_and_show_instructions(prompt_output_file, merged_prompt, next_step, next_file)

    # Check and handle existing next step file (always do this)
    _handle_next_step_file(next_file, next_step, lock, prompt_output_file)
