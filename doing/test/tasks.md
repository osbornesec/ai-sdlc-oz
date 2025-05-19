

**Core Problems Identified:**

1.  **Fragility on Missing Prompt Files:** If a prompt template (e.g., `prompts/02-prd-prompt.md`) is deleted, `aisdlc next` fails without a good recovery path.
2.  **Lack of Recovery Options:** When such a failure occurs, the user wants choices:
    *   Select a different step (though this might break the logical flow).
    *   Recreate the missing file (specifically, the prompt template, or potentially a previous step's output).
3.  **Desire for Proactive File Monitoring (Advanced):** Ideally, the system would detect if a *generated step file* (e.g., `doing/<slug>/01-idea-<slug>.md`) is deleted and offer to recreate it. This is a more complex feature involving file system watching.
4.  **Need for Constant Context:** After each command, a reminder of the current workstream status would be beneficial for user orientation.

Let's address these, prioritizing practicality and impact.

**Proposed Solutions & Enhancements:**

**1. Contextual Status Reminder (High Impact, Low-Medium Complexity)**

This is a great UX improvement. We can modify the `cli.py` to display a compact status after most successful command executions.

*   **File to Modify:** `ai_sdlc/cli.py`
*   **Logic:**
    *   Create a helper function, say `_display_compact_status()`, that reuses parts of `ai_sdlc.commands.status.run_status()` but prints a more concise output.
    *   In `main()`, after a command handler executes successfully, call this helper function (unless the command was `status` itself, or `init` if no lock file exists yet).

```diff
--- a/ai_sdlc/cli.py
+++ b/ai_sdlc/cli.py
@@ -5,6 +5,7 @@
 import sys
 from importlib import import_module
 from typing import Callable, Dict
+from .utils import read_lock, load_config # Added for status display
 
 _COMMANDS: Dict[str, str] = {
     "init": "ai_sdlc.commands.init:run_init",
@@ -19,16 +20,36 @@
     module_name, func_name = dotted.split(":")
     module = import_module(module_name)
     return getattr(module, func_name)
+
+def _display_compact_status() -> None:
+    """Displays a compact version of the current workstream status."""
+    lock = read_lock()
+    if not lock or "slug" not in lock:
+        return # No active workstream or invalid lock
+
+    try:
+        conf = load_config()
+        steps = conf["steps"]
+        slug = lock.get("slug", "N/A")
+        current_step_name = lock.get("current", "N/A")
+
+        if current_step_name in steps:
+            idx = steps.index(current_step_name)
+            bar = " ▸ ".join([("✅" if i <= idx else "☐") + s[2:] for i, s in enumerate(steps)])
+            print(f"\n---\n📌 Current: {slug} @ {current_step_name}\n   {bar}\n---")
+        else:
+            print(f"\n---\n📌 Current: {slug} @ {current_step_name} (Step not in config)\n---")
+    except FileNotFoundError: # .aisdlc missing
+        print("\n---\n📌 AI-SDLC config (.aisdlc) not found. Cannot display status.\n---")
+    except Exception: # Catch other potential errors during status display
+        print("\n---\n📌 Could not display current status due to an unexpected issue.\n---")
 
 
 def main() -> None:  # noqa: D401
     """Run the requested sub-command."""
     cmd, *args = sys.argv[1:] or ["--help"]
     if cmd not in _COMMANDS:
-        valid = "|".join(_COMMANDS.keys())
-        print(f"Usage: aisdlc [{valid}]")
+        print(f"Usage: aisdlc [{ '|'.join(_COMMANDS.keys()) }] [--help]")
         sys.exit(1)
 
     handler = _resolve(_COMMANDS[cmd])
-    handler(args) if args else handler()
+    handler(args) if args else handler() # Execute command
+
+    # Display status after most commands, unless it's status itself or init (before lock exists)
+    if cmd not in ["status", "init"] :
+        _display_compact_status()
 
 
 if __name__ == "__main__":

```

**2. Handling Missing Prompt Files (`prompts/<step>-prompt.md`)**

The current behavior in `ai_sdlc/commands/next.py` is:
```python
    if not prompt_file.exists():
        print(f"❌  Prompt file {prompt_file} missing.")
        return
```
This is a clear error. The core issue is that these prompt templates are fundamental to the tool's operation and are typically scaffolded by `aisdlc init` or manually curated by the user/team. The tool itself doesn't *generate* these prompt templates.

*   **Recommendation:**
    *   The current error message is appropriate. The user needs to ensure their `prompts/` directory is intact (e.g., restore from version control, re-run `aisdlc init` in a *fresh* directory and copy over, or manually recreate the specific prompt template).
    *   **Why not offer to "recreate" or "choose another step"?**
        *   **Recreate:** The tool doesn't have a "master" copy of these prompt templates post-init to recreate from. It would be complex to bundle all default prompts within the package just for this rare case.
        *   **Choose another step:** This breaks the chain-of-thought design. Step `N`'s prompt relies on the output of step `N-1`. Skipping a step or jumping around would lead to incoherent AI generation.

    *   **Slight Enhancement to Error Message (Optional):**
        ```python
        if not prompt_file.exists():
            print(f"❌ Critical Error: Prompt template file '{prompt_file}' is missing.")
            print(f"   This file is essential for generating the '{next_step}' step.")
            print(f"   Please ensure it exists in your '{conf['prompt_dir']}/' directory.")
            print(f"   You may need to restore it from version control or your initial 'aisdlc init' setup.")
            sys.exit(1) # Make it a harder exit
        ```
        This makes the error more explicit and guides the user towards the correct fix (manual restoration).

**3. Handling Missing *Generated Step Files* (`doing/<slug>/<prev_step>-<slug>.md`)**

This is when `prev_file` in `aisdlc next` is missing. The current behavior is:
```python
    if not prev_file.exists():
        print(f"❌  Expected file {prev_file} not found.")
        return
```
This is also a situation where the user has likely manually intervened (e.g., deleted the file).

*   **Recommendation:**
    *   Similar to missing prompt templates, the primary responsibility for managing these generated files lies with the user and their version control.
    *   **Why not offer to "regenerate" or "go back"?**
        *   **Regenerate `prev_step`:** If `prev_step` was AI-generated, re-running its generation might produce different content. If it was the *first* step (`01-idea`), it was manually created; the tool can't guess its content. This requires knowing the input to the *previous* AI call, which adds complexity.
        *   **Go back (modify `.aisdlc.lock`):** This is a manual recovery the user can perform if they understand the implications. The tool could offer this, but it's safer to let the user decide to edit the lock file or restart the step.

    *   **Slight Enhancement to Error Message (Optional):**
        ```python
        if not prev_file.exists():
            print(f"❌ Error: The previous step's output file '{prev_file}' is missing.")
            print(f"   This file is required as input to generate the '{next_step}' step.")
            print(f"   Please restore this file (e.g., from version control) or ensure it was correctly generated.")
            print(f"   If you need to restart the '{prev_step}', you might need to adjust '.aisdlc.lock' or re-run the command that generates '{prev_step}'.")
            sys.exit(1) # Make it a harder exit
        ```

**4. Proactive File Monitoring (File System Watching)**

This is a significant feature addition:

*   **Complexity:** Requires integrating a library like `watchdog`.
*   **Behavior:** Needs careful design. What if a file is temporarily deleted during a refactor? How to distinguish accidental vs. intentional deletion?
*   **Recommendation:** Defer this to a future version. It adds substantial complexity for a benefit that might be niche. Good version control practices by the user are a more robust solution for file recovery.

**Summary of Changes to Implement Now:**

1.  **Implement the contextual status reminder** in `ai_sdlc/cli.py`. This is a clear UX win.
2.  (Optional but good) **Enhance the error messages** in `ai_sdlc/commands/next.py` for missing `prompt_file` and `prev_file` to be more instructive and use `sys.exit(1)`.

The core principle remains: `aisdlc` orchestrates a linear flow. The integrity of the `prompts/` directory and the generated `doing/` files is crucial. The tool should be clear when these prerequisites are not met, guiding the user to fix the state rather than trying to perform complex, potentially non-deterministic "magic" recovery.

Let me know if you'd like me to proceed with generating the diff for the contextual status reminder and the enhanced error messages!