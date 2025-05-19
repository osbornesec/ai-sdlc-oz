import json
import subprocess
from pathlib import Path

import pytest

# This assumes 'aisdlc' is installed and in PATH, or you can call it via 'python -m ai_sdlc.cli'
AISDLC_CMD = ["aisdlc"]  # Or ["python", "-m", "ai_sdlc.cli"]


def run_aisdlc_command(cwd: Path, *args):
    """Helper to run aisdlc commands in tests."""
    return subprocess.run(
        AISDLC_CMD + list(args),
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,  # Handle non-zero exit codes in tests
    )


@pytest.fixture
def mock_cursor_agent(mocker):
    """Mock the cursor agent subprocess call to return predictable output."""

    def _mock_cursor_agent_call(
        cmd_args, text=True, timeout=None, **kwargs
    ):  # Added **kwargs for check_output
        # cmd_args[3] is the path to the temporary prompt file when using "cursor agent --file <path>"
        # The actual command is ['cursor', 'agent', '--file', tmp_prompt_path_str]
        prompt_file_path_str = cmd_args[3]

        mock_output = (
            "# Mock Generic Content\n\nThis is a generic mock response for testing."
        )
        try:
            prompt_content = Path(prompt_file_path_str).read_text()
            # Check for keywords from prompt templates to return specific mock content
            if (
                "01-idea-prompt.md" in prompt_content
            ):  # This won't happen as 01-idea is user-filled
                mock_output = "# Mock Idea Analysis\n\nThis is a mock idea analysis."
            elif (
                "02-prd-prompt.md" in prompt_content
                or "PRD Prompt Template" in prompt_content
            ):  # Check for unique string from template
                mock_output = "# Mock PRD Content\n\n## Overview\n\nThis is a mock PRD for testing."
            elif "03-prd-plus-prompt.md" in prompt_content:
                mock_output = "# Mock PRD Plus Content\n\n## Additional Details\n\nThis is a mock PRD+ for testing."
            # Add more conditions for other steps if needed
        except (IndexError, FileNotFoundError):
            # Fallback to generic if prompt file can't be read or path is unexpected
            pass

        # subprocess.check_output returns bytes by default unless text=True
        # The mock should return string if text=True is expected by the caller
        if "text" in kwargs and kwargs["text"]:
            return mock_output
        return mock_output.encode("utf-8")

    # Patch subprocess.check_output as that's what ai_sdlc.commands.next uses
    return mocker.patch("subprocess.check_output", side_effect=_mock_cursor_agent_call)


def test_full_lifecycle_flow(temp_project_dir: Path, mock_cursor_agent, mocker):
    """Test the entire aisdlc workflow from init through next to done."""

    # Patch ROOT to point to our temp directory for all utils functions
    mocker.patch("ai_sdlc.utils.ROOT", temp_project_dir)
    mocker.patch("ai_sdlc.commands.init.ROOT", temp_project_dir)
    mocker.patch("ai_sdlc.commands.new.ROOT", temp_project_dir)
    mocker.patch("ai_sdlc.commands.next.ROOT", temp_project_dir)
    mocker.patch("ai_sdlc.commands.done.ROOT", temp_project_dir)
    mocker.patch("ai_sdlc.commands.status.ROOT", temp_project_dir)

    # 1. Run init command
    # This will now create .aisdlc, prompts/, doing/, done/, .aisdlc.lock
    result = run_aisdlc_command(temp_project_dir, "init")
    assert result.returncode == 0, f"init failed: {result.stdout}\n{result.stderr}"

    # Verify files and directories created by init
    assert (temp_project_dir / ".aisdlc").exists()
    assert (temp_project_dir / "prompts").is_dir()
    assert (temp_project_dir / "prompts" / "01-idea-prompt.md").exists()
    assert (
        temp_project_dir / "prompts" / "02-prd-prompt.md"
    ).exists()  # Check one of the key prompts for 'next'
    assert (temp_project_dir / "doing").is_dir()
    assert (temp_project_dir / "done").is_dir()
    assert (temp_project_dir / ".aisdlc.lock").exists()

    # Load the created .aisdlc to get steps for further testing
    # Note: utils.load_config() will use the patched ROOT
    config = json.loads(
        (temp_project_dir / ".aisdlc.lock").read_text()
    )  # Read lock first
    assert config == {}  # Init creates an empty lock

    # Read .aisdlc config to confirm steps (it's TOML, not JSON)
    # For simplicity, we'll assume the default steps from the template for now.
    # A more robust test could parse the .aisdlc TOML file.
    # For this test, we'll use a simplified list of steps matching the old test structure.
    # Or, better, load the config properly.
    # We need to ensure load_config() works with the patched ROOT.
    # The test for load_config itself should cover this.
    # For this integration test, let's assume default steps.

    # To make the test robust against changes in default .aisdlc,
    # we should parse the .aisdlc file that `init` creates.
    import tomli

    aisdlc_config_content = (temp_project_dir / ".aisdlc").read_text()
    aisdlc_config = tomli.loads(aisdlc_config_content)
    test_steps = aisdlc_config["steps"]  # Use actual steps from scaffolded config

    # 2. Run new command
    idea_title = "My Test Idea"
    idea_slug = "my-test-idea"  # utils.slugify(idea_title)
    result = run_aisdlc_command(temp_project_dir, "new", idea_title)
    assert result.returncode == 0, f"new failed: {result.stdout}\n{result.stderr}"

    idea_file = (
        temp_project_dir / "doing" / idea_slug / f"{test_steps[0]}-{idea_slug}.md"
    )
    assert idea_file.exists()
    assert idea_title in idea_file.read_text()

    lock_file = temp_project_dir / ".aisdlc.lock"
    assert lock_file.exists()
    lock_content = json.loads(lock_file.read_text())
    assert lock_content["slug"] == idea_slug
    assert lock_content["current"] == test_steps[0]  # e.g., "01-idea"

    # 3. Run next command (advancing from 01-idea to 02-prd)
    # This relies on our mock_cursor_agent and the 02-prd-prompt.md created by init
    result = run_aisdlc_command(temp_project_dir, "next")
    assert result.returncode == 0, (
        f"next (to {test_steps[1]}) failed: {result.stdout}\n{result.stderr}"
    )

    next_step_file = (
        temp_project_dir / "doing" / idea_slug / f"{test_steps[1]}-{idea_slug}.md"
    )
    assert next_step_file.exists()
    # Check content from mock_cursor_agent
    assert "Mock PRD Content" in next_step_file.read_text()

    lock_content = json.loads(lock_file.read_text())
    assert lock_content["current"] == test_steps[1]  # e.g., "02-prd"

    # 4. Run next command again (advancing from 02-prd to 03-prd-plus)
    # Ensure a prompt file for 03-prd-plus-prompt.md exists from init
    assert (temp_project_dir / "prompts" / f"{test_steps[2]}-prompt.md").exists()

    result = run_aisdlc_command(temp_project_dir, "next")
    assert result.returncode == 0, (
        f"next (to {test_steps[2]}) failed: {result.stdout}\n{result.stderr}"
    )

    next_step_file_2 = (
        temp_project_dir / "doing" / idea_slug / f"{test_steps[2]}-{idea_slug}.md"
    )
    assert next_step_file_2.exists()
    assert "Mock PRD Plus Content" in next_step_file_2.read_text()

    lock_content = json.loads(lock_file.read_text())
    assert lock_content["current"] == test_steps[2]  # e.g., "03-prd-plus"

    # 5. Run done command (after advancing through all steps)
    # For a full test, we'd loop `next` until the last step.
    # For now, let's manually set the lock to the last step.
    lock_content["current"] = test_steps[-1]
    lock_file.write_text(json.dumps(lock_content))

    # Create dummy files for all steps to satisfy `done` command's checks
    active_dir_path = temp_project_dir / aisdlc_config["active_dir"] / idea_slug
    for step_name in test_steps:
        (active_dir_path / f"{step_name}-{idea_slug}.md").touch()

    result = run_aisdlc_command(temp_project_dir, "done")
    assert result.returncode == 0, f"done failed: {result.stdout}\n{result.stderr}"

    # Check if workdir was moved to done_dir
    done_dir_path = temp_project_dir / aisdlc_config["done_dir"] / idea_slug
    assert done_dir_path.exists()
    assert not active_dir_path.exists()  # Original should be gone

    # Check lock file is now empty
    lock_content = json.loads(lock_file.read_text())
    assert lock_content == {}
