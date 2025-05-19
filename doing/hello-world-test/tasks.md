Okay, here's a detailed task list based on the previous review, including specific paths, file names, actionables, and code snippets/diffs where appropriate.

---

## Task List for `ai-sdlc` Improvements

### 1. Error Handling and Robustness

**Task 1.1: Improve Cursor Agent Error Handling in `ai_sdlc/commands/next.py`**

*   **File:** `ai_sdlc/commands/next.py`
*   **Actionable:** Enhance the error message when the `cursor agent` subprocess fails to include `stdout` and `stderr` for better debugging.
*   **Details:**
    ```diff
    --- a/ai_sdlc/commands/next.py
    +++ b/ai_sdlc/commands/next.py
    @@ -30,7 +30,9 @@
                 text=True,
             )
         except subprocess.CalledProcessError as e:
    -        print("❌  Cursor agent failed:", e)
    +        print(f"❌  Cursor agent failed with exit code {e.returncode}.")
    +        if e.stdout: print(f"Stdout:\n{e.stdout}")
    +        if e.stderr: print(f"Stderr:\n{e.stderr}")
             sys.exit(1)

         next_file.write_text(output)

    ```

**Task 1.2: Add Timeout to Cursor Agent Call in `ai_sdlc/commands/next.py`**

*   **File:** `ai_sdlc/commands/next.py`
*   **Actionable:** Add a `timeout` to the `subprocess.check_output` call to prevent indefinite hangs. Catch `subprocess.TimeoutExpired`.
*   **Details:**
    ```python
    # ai_sdlc/commands/next.py
    # Define a reasonable timeout, e.g., 5 minutes (300 seconds)
    CURSOR_AGENT_TIMEOUT = 300
    ```
    ```diff
    --- a/ai_sdlc/commands/next.py
    +++ b/ai_sdlc/commands/next.py
    @@ -27,12 +27,17 @@
     try:
         output = subprocess.check_output(
             ["cursor", "agent", "--file", str(tmp_prompt)],
             text=True,
    +        timeout=CURSOR_AGENT_TIMEOUT, # Add timeout
         )
     except subprocess.CalledProcessError as e:
    -    print("❌  Cursor agent failed:", e)
    +    print(f"❌  Cursor agent failed with exit code {e.returncode}.")
    +    if e.stdout: print(f"Stdout:\n{e.stdout}")
    +    if e.stderr: print(f"Stderr:\n{e.stderr}")
    +    sys.exit(1)
    +except subprocess.TimeoutExpired:
    +    print(f"❌  Cursor agent timed out after {CURSOR_AGENT_TIMEOUT} seconds.")
         sys.exit(1)

     next_file.write_text(output)
    ```

**Task 1.3: Add File I/O Error Handling in Commands**

*   **Files:** `ai_sdlc/commands/new.py`, `ai_sdlc/commands/done.py`, `ai_sdlc/commands/next.py`, `ai_sdlc/utils.py` (for `write_lock`)
*   **Actionable:** Wrap file system operations (`write_text`, `shutil.move`, `mkdir`) in `try...except OSError` blocks.
*   **Details (Example for `ai_sdlc/commands/new.py`):**
    ```diff
    --- a/ai_sdlc/commands/new.py
    +++ b/ai_sdlc/commands/new.py
    @@ -16,19 +16,26 @@
         print(f"❌  Work-stream '{slug}' already exists.")
         sys.exit(1)

    -    workdir.mkdir(parents=True)
    -    idea_file = workdir / f"01-idea-{slug}.md"
    -    idea_file.write_text(
    -        f"# {idea_text}\n\n## Problem\n\n## Solution\n\n## Rabbit Holes\n",
    -    )
    +    try:
    +        workdir.mkdir(parents=True)
    +        idea_file = workdir / f"01-idea-{slug}.md"
    +        idea_file.write_text(
    +            f"# {idea_text}\n\n## Problem\n\n## Solution\n\n## Rabbit Holes\n",
    +        )
    +
    +        write_lock(
    +            {
    +                "slug": slug,
    +                "current": "01-idea",
    +                "created": datetime.datetime.utcnow().isoformat(),
    +            },
    +        )
    +        print(f"✅  Created {idea_file}.  Fill it out, then run `aisdlc next`.")
    +    except OSError as e:
    +        print(f"❌  Error creating work-stream files for '{slug}': {e}")
    +        # Potentially attempt cleanup if partial files were created
    +        sys.exit(1)

    -    write_lock(
    -        {
    -            "slug": slug,
    -            "current": "01-idea",
    -            "created": datetime.datetime.utcnow().isoformat(),
    -        },
    -    )
    -    print(f"✅  Created {idea_file}.  Fill it out, then run `aisdlc next`.")
    ```
    *   **Apply similar `try...except OSError` blocks to:**
        *   `ai_sdlc/commands/done.py`: around `shutil.move` and `write_lock`.
        *   `ai_sdlc/commands/next.py`: around `next_file.write_text` and `write_lock`.
        *   `ai_sdlc/utils.py`: in `write_lock` around `write_text`.

**Task 1.4: Add Lock File Corruption Handling in `ai_sdlc/utils.py`**

*   **File:** `ai_sdlc/utils.py`
*   **Actionable:** Catch `json.JSONDecodeError` in `read_lock()` and provide a helpful message.
*   **Details:**
    ```diff
    --- a/ai_sdlc/utils.py
    +++ b/ai_sdlc/utils.py
    @@ -24,7 +24,13 @@

 def read_lock() -> dict:
     path = ROOT / ".aisdlc.lock"
    -    return json.loads(path.read_text()) if path.exists() else {}
    +    if not path.exists():
    +        return {}
    +    try:
    +        return json.loads(path.read_text())
    +    except json.JSONDecodeError:
    +        print("⚠️  Warning: '.aisdlc.lock' file is corrupted or not valid JSON. Treating as empty.")
    +        return {} # Or sys.exit(1) if strictness is preferred


 def write_lock(data: dict) -> None:
    ```

**Task 1.5: Add Config File Corruption Handling in `ai_sdlc/utils.py`**

*   **File:** `ai_sdlc/utils.py`
*   **Actionable:** Catch `_toml.TOMLDecodeError` (or equivalent for `tomli`) in `load_config()`.
*   **Details:**
    ```diff
    --- a/ai_sdlc/utils.py
    +++ b/ai_sdlc/utils.py
    @@ -14,7 +14,12 @@
     cfg_path = ROOT / ".aisdlc"
     if not cfg_path.exists():
         raise FileNotFoundError(".aisdlc manifest missing – run `aisdlc init`.")
    -    return _toml.loads(cfg_path.read_text())
    +    try:
    +        return _toml.loads(cfg_path.read_text())
    +    except _toml.TOMLDecodeError as e: # For tomllib, it's tomllib.TOMLDecodeError
    +        print(f"❌ Error: '.aisdlc' configuration file is corrupted: {e}")
    +        print("Please fix the .aisdlc file or run 'aisdlc init' in a new directory.")
    +        sys.exit(1) # Added import sys at the top of utils.py


 def slugify(text: str) -> str:
    ```
    *   Ensure `import sys` is added to `ai_sdlc/utils.py`.

---

### 2. Temporary File Management

**Task 2.1: Implement Secure Temporary File Handling in `ai_sdlc/commands/next.py`**

*   **File:** `ai_sdlc/commands/next.py`
*   **Actionable:** Replace hardcoded `/tmp/aisdlc_prompt.md` with `tempfile.NamedTemporaryFile`.
*   **Details:**
    ```diff
    --- a/ai_sdlc/commands/next.py
    +++ b/ai_sdlc/commands/next.py
    @@ -2,6 +2,7 @@
     from __future__ import annotations

     import subprocess
    +import tempfile
     import sys
     from pathlib import Path

    @@ -22,22 +23,30 @@
         return

     merged_prompt = prompt_file.read_text().replace(PLACEHOLDER, prev_file.read_text())
    -    tmp_prompt = Path("/tmp/aisdlc_prompt.md")
    -    tmp_prompt.write_text(merged_prompt)
    +    tmp_prompt_path_str = None # Initialize for finally block
    +    try:
    +        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".md", encoding="utf-8") as tmp_file_obj:
    +            tmp_prompt_path_str = tmp_file_obj.name
    +            tmp_file_obj.write(merged_prompt)

    -    print(f"🧠  Calling Cursor agent for step {next_step} …")
    -    try:
-        output = subprocess.check_output(
    -            ["cursor", "agent", "--file", str(tmp_prompt)],
    -            text=True,
    -        )
    -    except subprocess.CalledProcessError as e:
    -        print("❌  Cursor agent failed:", e)
    -        sys.exit(1)
    +        print(f"🧠  Calling Cursor agent for step {next_step} …")
    +        try:
    +            output = subprocess.check_output(
    +                ["cursor", "agent", "--file", tmp_prompt_path_str],
    +                text=True,
    +                timeout=CURSOR_AGENT_TIMEOUT,
    +            )
    +        except subprocess.CalledProcessError as e:
    +            print(f"❌  Cursor agent failed with exit code {e.returncode}.")
    +            if e.stdout: print(f"Stdout:\n{e.stdout}")
    +            if e.stderr: print(f"Stderr:\n{e.stderr}")
    +            sys.exit(1)
    +        except subprocess.TimeoutExpired:
    +            print(f"❌  Cursor agent timed out after {CURSOR_AGENT_TIMEOUT} seconds.")
    +            sys.exit(1)
    +    finally:
    +        if tmp_prompt_path_str and Path(tmp_prompt_path_str).exists():
    +            Path(tmp_prompt_path_str).unlink()

     next_file.write_text(output)
     lock["current"] = next_step

    ```

---

### 3. Configuration and Constants

**Task 3.1: (Optional/Consideration) Robust Project Root Detection**

*   **File:** `ai_sdlc/utils.py`
*   **Actionable:** (Consider for future enhancement) Modify `ROOT` detection to search upwards for `.aisdlc` if not found in `Path.cwd()`.
*   **Details:** This is more involved. For now, ensure documentation clearly states the CLI must be run from the repo root. If implemented, the logic would look something like:
    ```python
    # ai_sdlc/utils.py
    def find_project_root() -> Path:
        current_dir = Path.cwd()
        for parent in [current_dir] + list(current_dir.parents):
            if (parent / ".aisdlc").exists():
                return parent
        # Fallback or error
        print("Error: .aisdlc not found. Ensure you are in an ai-sdlc project directory.")
        sys.exit(1)

    ROOT = find_project_root()
    ```
    This change would affect how `ROOT` is defined and used globally.

---

### 4. Testing Strategy for `ai-sdlc`

**Task 4.1: Set up Pytest and Basic Test Structure**

*   **Files:** `pyproject.toml`, `tests/conftest.py` (new), `tests/__init__.py` (new)
*   **Actionable:**
    1.  Add `pytest` and `pytest-mock` to `dev` dependencies in `pyproject.toml`.
        ```toml
        # pyproject.toml
        [project.optional-dependencies]
        dev = [
            "pytest>=7.0",
            "pytest-mock>=3.0",
            # Add other dev tools like ruff, pyright if not already there
        ]
        ```
    2.  Create a `tests/` directory at the project root.
    3.  Create `tests/__init__.py` (can be empty).
    4.  Create `tests/conftest.py` for shared fixtures (e.g., a temporary directory for tests).
        ```python
        # tests/conftest.py
        import pytest
        import tempfile
        from pathlib import Path
        import shutil

        @pytest.fixture
        def temp_project_dir(tmp_path: Path):
            """Creates a temporary directory simulating a project root."""
            # tmp_path is a pytest fixture providing a temporary directory unique to the test
            # For more complex setups, you might copy baseline files here
            return tmp_path
        ```

**Task 4.2: Create Unit Tests for `ai_sdlc/utils.py`**

*   **File:** `tests/unit/test_utils.py` (new)
*   **Actionable:** Write unit tests for `slugify`, `load_config` (mocking file content), `read_lock`, `write_lock`.
*   **Details (Example for `slugify` and `load_config`):**
    ```python
    # tests/unit/test_utils.py
    import pytest
    from pathlib import Path
    import json
    from ai_sdlc import utils

    # Mock tomllib for testing load_config if it's not the stdlib version
    # Or ensure your test environment has the correct Python version / tomli installed

    def test_slugify():
        assert utils.slugify("Hello World!") == "hello-world"
        assert utils.slugify("  Test Slug with Spaces  ") == "test-slug-with-spaces"
        assert utils.slugify("Special!@#Chars") == "special-chars"
        assert utils.slugify("") == "idea" # As per current implementation

    def test_load_config_success(temp_project_dir: Path, mocker):
        mock_aisdlc_content = """
        version = "0.1.0"
        steps = ["01-idea", "02-prd"]
        prompt_dir = "prompts"
        """
        aisdlc_file = temp_project_dir / ".aisdlc"
        aisdlc_file.write_text(mock_aisdlc_content)

        mocker.patch('ai_sdlc.utils.ROOT', temp_project_dir) # Ensure ROOT points to test dir

        config = utils.load_config()
        assert config["version"] == "0.1.0"
        assert config["steps"] == ["01-idea", "02-prd"]

    def test_load_config_missing(temp_project_dir: Path, mocker):
        mocker.patch('ai_sdlc.utils.ROOT', temp_project_dir)
        with pytest.raises(FileNotFoundError, match="manifest missing"):
            utils.load_config()

    def test_load_config_corrupted(temp_project_dir: Path, mocker):
        aisdlc_file = temp_project_dir / ".aisdlc"
        aisdlc_file.write_text("this is not valid toml content {") # Corrupted TOML
        mocker.patch('ai_sdlc.utils.ROOT', temp_project_dir)
        mocker.patch('sys.exit') # Prevent test suite from exiting

        with pytest.raises(SystemExit): # Or check for printed error message
             utils.load_config()
        utils.sys.exit.assert_called_once_with(1)


    def test_read_write_lock(temp_project_dir: Path, mocker):
        mocker.patch('ai_sdlc.utils.ROOT', temp_project_dir)
        lock_data = {"slug": "test-slug", "current": "01-idea"}

        # Test write_lock
        utils.write_lock(lock_data)
        lock_file = temp_project_dir / ".aisdlc.lock"
        assert lock_file.exists()
        assert json.loads(lock_file.read_text()) == lock_data

        # Test read_lock
        read_data = utils.read_lock()
        assert read_data == lock_data

        # Test read_lock when file doesn't exist
        lock_file.unlink()
        assert utils.read_lock() == {}

        # Test read_lock with corrupted JSON
        lock_file.write_text("not json {")
        # Capture stdout to check for warning, or modify read_lock to raise on corruption for testing
        assert utils.read_lock() == {} # Assuming it returns {} on corruption as per Task 1.4
    ```

**Task 4.3: Create Unit Tests for `ai_sdlc/commands/*` (mocking dependencies)**

*   **Files:** `tests/unit/test_init_command.py`, `tests/unit/test_new_command.py`, etc.
*   **Actionable:** For each command, test its `run_*` function. Mock file system operations (`Path.mkdir`, `Path.write_text`, `shutil.move`), `utils.load_config`, `utils.read_lock`, `utils.write_lock`, and `subprocess.check_output`.
*   **Details (Example for `test_init_command.py`):**
    ```python
    # tests/unit/test_init_command.py
    import pytest
    from pathlib import Path
    from ai_sdlc.commands import init
    from ai_sdlc import utils

    def test_run_init(temp_project_dir: Path, mocker):
        mocker.patch('ai_sdlc.utils.ROOT', temp_project_dir)
        mock_write_lock = mocker.patch('ai_sdlc.utils.write_lock')

        init.run_init()

        assert (temp_project_dir / "doing").is_dir()
        assert (temp_project_dir / "done").is_dir()
        mock_write_lock.assert_called_once_with({})
        # Could also capture stdout to check print message
    ```

**Task 4.4: Create Integration Tests for CLI (mocking `cursor agent`)**

*   **File:** `tests/integration/test_cli_flow.py` (new)
*   **Actionable:** Use `subprocess.run` to execute `aisdlc` commands. Assert file system state and lock file content. Mock the `cursor agent` call within the `next` command's execution path.
*   **Details:** This is more complex. You might need to:
    1.  Create a helper script that `aisdlc next` can call instead of the real `cursor agent`, which writes predictable output.
    2.  Or, use `pytest-mock` to patch `subprocess.check_output` globally for these tests.
    ```python
    # tests/integration/test_cli_flow.py
    import pytest
    import subprocess
    import json
    from pathlib import Path

    # This assumes 'aisdlc' is installed and in PATH, or you can call it via 'python -m ai_sdlc.cli'
    AISDLC_CMD = ["aisdlc"] # Or ["python", "-m", "ai_sdlc.cli"]

    def run_aisdlc_command(cwd: Path, *args):
        return subprocess.run(
            AISDLC_CMD + list(args),
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False # Handle non-zero exit codes in tests
        )

    @pytest.fixture
    def mock_cursor_agent(mocker):
        def _mock_cursor_agent_call(cmd_args, text, timeout):
            # cmd_args[2] is the path to the temporary prompt file
            # For simplicity, just return a fixed string.
            # A more advanced mock could read the input prompt and return step-specific content.
            if "02-prd-prompt.md" in Path(cmd_args[2]).read_text(): # Rough check
                 return subprocess.CompletedProcess(args=cmd_args, returncode=0, stdout="# Mock PRD Content")
            if "03-prd-plus-prompt.md" in Path(cmd_args[2]).read_text():
                 return subprocess.CompletedProcess(args=cmd_args, returncode=0, stdout="# Mock PRD Plus Content")
            # ... and so on for other steps
            return subprocess.CompletedProcess(args=cmd_args, returncode=0, stdout="# Mock Generic Content")

        return mocker.patch('subprocess.check_output', side_effect=_mock_cursor_agent_call)


    def test_full_lifecycle_flow(temp_project_dir: Path, mock_cursor_agent, mocker):
        # 1. Init
        # Copy minimal .aisdlc and prompt files to temp_project_dir
        # For a real test, you'd copy your actual .aisdlc and prompt templates
        (temp_project_dir / ".aisdlc").write_text('version = "0.1.0"\nsteps = ["01-idea", "02-prd"]\nprompt_dir="prompts"\nactive_dir="doing"\ndone_dir="done"')
        prompts_dir = temp_project_dir / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "01-idea-prompt.md").write_text("Idea prompt template") # Not used by 'new'
        (prompts_dir / "02-prd-prompt.md").write_text("<prev_step></prev_step>\nPRD Prompt")


        result = run_aisdlc_command(temp_project_dir, "init")
        assert result.returncode == 0
        assert (temp_project_dir / "doing").exists()
        assert (temp_project_dir / "done").exists()
        assert json.loads((temp_project_dir / ".aisdlc.lock").read_text()) == {}

        # 2. New
        idea_title = "My Test Idea"
        idea_slug = "my-test-idea"
        result = run_aisdlc_command(temp_project_dir, "new", idea_title)
        assert result.returncode == 0
        idea_file = temp_project_dir / "doing" / idea_slug / f"01-idea-{idea_slug}.md"
        assert idea_file.exists()
        assert idea_title in idea_file.read_text()
        lock_content = json.loads((temp_project_dir / ".aisdlc.lock").read_text())
        assert lock_content["slug"] == idea_slug
        assert lock_content["current"] == "01-idea"

        # 3. Next (to PRD)
        result = run_aisdlc_command(temp_project_dir, "next")
        assert result.returncode == 0, f"Next command failed. Stderr: {result.stderr}"
        prd_file = temp_project_dir / "doing" / idea_slug / f"02-prd-{idea_slug}.md"
        assert prd_file.exists()
        assert "# Mock PRD Content" in prd_file.read_text() # From mock_cursor_agent
        lock_content = json.loads((temp_project_dir / ".aisdlc.lock").read_text())
        assert lock_content["current"] == "02-prd"

        # (Add more 'next' steps if your mock_cursor_agent and .aisdlc steps support it)

        # 4. Done (assuming all steps are 'completed' by mocks)
        # For this to pass, all 7 files for the '02-prd' step (or last step) would need to exist.
        # This test would need to be more elaborate to simulate all files being created.
        # For now, let's assume '02-prd' is the last step for this simplified test.
        # To make 'done' work, we'd need to manually create the expected files or have the mock 'next' create them.
        # Or, adjust the 'done' command's logic for testing if it's too complex to mock all files.

        # Example: If '02-prd' was the last step in a simplified .aisdlc for this test
        # result = run_aisdlc_command(temp_project_dir, "done")
        # assert result.returncode == 0
        # assert (temp_project_dir / "done" / idea_slug).exists()
        # assert not (temp_project_dir / "doing" / idea_slug).exists()
        # assert json.loads((temp_project_dir / ".aisdlc.lock").read_text()) == {}
    ```

---

### 5. CLI User Experience

**Task 5.1: Add Verbose Output to `aisdlc next`**

*   **File:** `ai_sdlc/commands/next.py`
*   **Actionable:** Add `print` statements to indicate progress.
*   **Details:**
    ```diff
    --- a/ai_sdlc/commands/next.py
    +++ b/ai_sdlc/commands/next.py
    @@ -19,14 +19,20 @@
         print(f"❌  Expected file {prev_file} not found.")
         return
     if not prompt_file.exists():
    -    print(f"❌  Prompt {prompt_file} missing.")
    +    print(f"❌  Prompt file {prompt_file} missing.")
         return

    +print(f"ℹ️  Reading previous step from: {prev_file}")
    +prev_step_content = prev_file.read_text()
    +print(f"ℹ️  Reading prompt template from: {prompt_file}")
    +prompt_template_content = prompt_file.read_text()
    +
    -merged_prompt = prompt_file.read_text().replace(PLACEHOLDER, prev_file.read_text())
    +merged_prompt = prompt_template_content.replace(PLACEHOLDER, prev_step_content)
     tmp_prompt_path_str = None # Initialize for finally block
     try:
         with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".md", encoding="utf-8") as tmp_file_obj:
    @@ -34,6 +40,7 @@
             tmp_file_obj.write(merged_prompt)

         print(f"🧠  Calling Cursor agent for step {next_step} …")
    +    print(f"   Using temporary prompt file: {tmp_prompt_path_str}")
         try:
             output = subprocess.check_output(
                 ["cursor", "agent", "--file", tmp_prompt_path_str],
    @@ -51,6 +58,7 @@
         if tmp_prompt_path_str and Path(tmp_prompt_path_str).exists():
             Path(tmp_prompt_path_str).unlink()

    +print(f"ℹ️  Cursor agent finished. Writing output to: {next_file}")
     next_file.write_text(output)
     lock["current"] = next_step
     write_lock(lock)

    ```

---

### 6. UV Usage Simplification

**Task 6.1: Review and Simplify UV Workflow in `README.md` and `pyproject.toml`**

*   **Files:** `README.md`, `pyproject.toml`
*   **Actionable:**
    1.  **`pyproject.toml`:**
        *   Ensure `[project.optional-dependencies]` for `dev` is present and includes `pytest`, `pytest-mock`, `ruff`, `pyright`.
        *   The current `[tool.uv]` settings (`virtualenvs.in-project = true`, `sync.subprocesses = true`) are good.
    2.  **`README.md` - Developer Setup:**
        *   Clarify `uv pip install -e .` vs `uv pip install -e .[dev]`.
        *   Emphasize `uv sync` for contributors to install from `uv.lock`.
        *   Ensure commands for linting/testing use `uv run` if appropriate (e.g., `uv run ruff check .`, `uv run pytest`). This ensures tools are run from the virtual environment managed by `uv`.
*   **Details (README.md diff example):**
    ```diff
    --- a/README.md
    +++ b/README.md
    @@ -21,15 +21,20 @@
     | **Node ≥ 20 / pnpm** *(optional)* | if you plan to extend any TypeScript helpers                | `brew install node pnpm`                                                  |      |

     ```bash
    -# clone & install *editable* for local hacking
    -uv pip install -e .
    -# run the test suite (pytest + ts‑jest if TS code present)
    -pytest -q
+    # Clone the repository
+    # git clone ...
+    # cd ai-sdlc

    -# For consistent dependencies using the lock file (contributors):
-    # uv sync
-    # To update the lock file after changing dependencies in pyproject.toml:
-    # uv lock
+    # Create/activate venv and install dependencies (for contributors, using the lock file):
+    uv venv # Creates .venv if it doesn't exist
+    uv sync # Installs dependencies from uv.lock, including dev dependencies if specified
+
+    # For developers making changes to dependencies in pyproject.toml:
+    # uv pip install -e .[dev] # Installs in editable mode with dev dependencies
+    # uv lock # After changing pyproject.toml, to update uv.lock
+
+    # Run linters and tests (ensure dev dependencies are installed):
+    uv run ruff check ai_sdlc tests
+    uv run pyright
+    uv run pytest -q
     ```

---
