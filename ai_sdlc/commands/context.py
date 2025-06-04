"""`aisdlc context` – manage Context7 library documentation integration."""

from __future__ import annotations

import sys

from ai_sdlc.services.context7_service import Context7Service
from ai_sdlc.types import ConfigDict, LockDict
from ai_sdlc.utils import ROOT, load_config, read_lock


def run_context(args: list[str] | None) -> None:
    """Manage Context7 documentation for current step.

    Args:
        args: Command line arguments for context command
              Supports --libraries, --show-cache, --clear-cache

    Raises:
        SystemExit: If no active workstream or invalid arguments
    """
    config: ConfigDict = load_config()
    lock: LockDict = read_lock()

    if not lock:
        print("❌  No active workstream. Run `aisdlc new` first.")
        sys.exit(1)

    # Parse arguments
    force_libraries: list[str] = []
    show_cache = False
    clear_cache = False

    if not args:
        args = []

    i = 0
    while i < len(args):
        if args[i] == "--libraries" and i + 1 < len(args):
            # Validate library names
            lib_list = args[i + 1].split(",")
            force_libraries = []
            for lib in lib_list:
                lib = lib.strip()
                # Validate library name (alphanumeric, dash, underscore)
                if not lib or not all(c.isalnum() or c in "-_" for c in lib):
                    print(f"❌  Error: Invalid library name: {lib}")
                    print(
                        "   Library names must contain only letters, numbers, hyphens, and underscores"
                    )
                    sys.exit(1)
                if len(lib) > 50:
                    print(f"❌  Error: Library name too long: {lib}")
                    sys.exit(1)
                force_libraries.append(lib)
            i += 2
        elif args[i] == "--show-cache":
            show_cache = True
            i += 1
        elif args[i] == "--clear-cache":
            clear_cache = True
            i += 1
        else:
            print(f"❌  Unknown argument: {args[i]}")
            print("\nUsage: aisdlc context [options]")
            print("Options:")
            print("  --libraries lib1,lib2  Force specific libraries")
            print("  --show-cache          Show cached documentation")
            print("  --clear-cache         Clear documentation cache")
            sys.exit(1)

    # Initialize Context7 service
    cache_dir = ROOT / ".context7_cache"
    context7 = Context7Service(cache_dir)

    # Handle cache operations
    if clear_cache:
        if cache_dir.exists():
            import shutil

            shutil.rmtree(cache_dir)
            cache_dir.mkdir()
        print("✅  Context7 cache cleared.")
        return

    if show_cache:
        if not cache_dir.exists() or not any(cache_dir.iterdir()):
            print("📭  Context7 cache is empty.")
        else:
            print("📚  Context7 Cache Contents:")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
            for file in sorted(cache_dir.glob("*.md")):
                size_kb = file.stat().st_size / 1024
                print(f"  • {file.stem}: {size_kb:.1f} KB")
        return

    # Get current step and content
    assert "slug" in lock and "current" in lock
    slug = lock["slug"]
    current_step = lock["current"]
    steps = config["steps"]
    step_index = steps.index(current_step)

    workdir = ROOT / config["active_dir"] / slug

    # Read all previous content to build context
    all_content = []
    for i in range(step_index + 1):
        step_file = workdir / f"{steps[i]}-{slug}.md"
        if step_file.exists():
            all_content.append(step_file.read_text())

    combined_content = "\n\n".join(all_content)

    # Detect or use forced libraries
    if force_libraries:
        detected_libraries = force_libraries
    else:
        detected_libraries = context7.extract_libraries_from_text(combined_content)

    # Generate output
    output = context7.create_context_command_output(current_step, detected_libraries)
    print(output)

    # If we're about to generate a prompt, show what will be included
    if step_index + 1 < len(steps):
        next_step = steps[step_index + 1]
        next_step_libraries = context7.get_step_specific_libraries(next_step)
        if next_step_libraries:
            print(f"\n📋 Recommended for next step ({next_step}):")
            for lib in next_step_libraries:
                if lib not in detected_libraries:
                    print(f"  • {lib} (add with: aisdlc context --libraries {lib})")


def main() -> None:
    """Entry point for testing."""
    import sys

    run_context(sys.argv[1:])


if __name__ == "__main__":
    main()
