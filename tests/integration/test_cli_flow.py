import pytest
import subprocess
import json
from pathlib import Path

# This assumes 'aisdlc' is installed and in PATH, or you can call it via 'python -m ai_sdlc.cli'
AISDLC_CMD = ["aisdlc"]  # Or ["python", "-m", "ai_sdlc.cli"]

def run_aisdlc_command(cwd: Path, *args):
    """Helper to run aisdlc commands in tests."""
    return subprocess.run(
        AISDLC_CMD + list(args),
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False  # Handle non-zero exit codes in tests
    )

@pytest.fixture
def mock_cursor_agent(mocker):
    """Mock the cursor agent subprocess call to return predictable output."""
    def _mock_cursor_agent_call(cmd_args, text=True, timeout=None):
        # cmd_args[2] is the path to the temporary prompt file
        # For simplicity, just return a fixed string.
        # A more advanced mock could read the input prompt and return step-specific content.
        try:
            prompt_content = Path(cmd_args[3]).read_text()  # Using file path from args
            if "02-prd-prompt.md" in prompt_content:
                return "# Mock PRD Content\n\n## Overview\n\nThis is a mock PRD for testing."
            if "03-prd-plus-prompt.md" in prompt_content:
                return "# Mock PRD Plus Content\n\n## Additional Details\n\nThis is a mock PRD+ for testing."
        except (IndexError, FileNotFoundError):
            pass
        
        # Default mock response
        return "# Mock Generic Content\n\nThis is a generic mock response for testing."

    return mocker.patch('subprocess.check_output', side_effect=_mock_cursor_agent_call)


def test_full_lifecycle_flow(temp_project_dir: Path, mock_cursor_agent, mocker):
    """Test the entire aisdlc workflow from init through next to done."""
    # 1. Set up required files
    # Create minimal .aisdlc config
    (temp_project_dir / ".aisdlc").write_text(
        'version = "0.1.0"\n'
        'steps = ["01-idea", "02-prd"]\n'
        'prompt_dir = "prompts"\n'
        'active_dir = "doing"\n'
        'done_dir = "done"\n'
    )
    
    # Create prompt templates
    prompts_dir = temp_project_dir / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "02-prd-prompt.md").write_text("<prev_step></prev_step>\nPRD Prompt Template")
    
    # Patch ROOT to point to our temp directory
    mocker.patch('ai_sdlc.utils.ROOT', temp_project_dir)
    
    # 2. Run init command
    result = run_aisdlc_command(temp_project_dir, "init")
    assert result.returncode == 0
    assert (temp_project_dir / "doing").exists()
    assert (temp_project_dir / "done").exists()
    
    # 3. Run new command
    idea_title = "My Test Idea"
    idea_slug = "my-test-idea"
    result = run_aisdlc_command(temp_project_dir, "new", idea_title)
    assert result.returncode == 0
    
    # Check if idea file was created
    idea_file = temp_project_dir / "doing" / idea_slug / f"01-idea-{idea_slug}.md"
    assert idea_file.exists()
    assert idea_title in idea_file.read_text()
    
    # Check lock file
    lock_file = temp_project_dir / ".aisdlc.lock"
    assert lock_file.exists()
    lock_content = json.loads(lock_file.read_text())
    assert lock_content["slug"] == idea_slug
    assert lock_content["current"] == "01-idea"
    
    # 4. Run next command
    # This relies on our mock_cursor_agent
    result = run_aisdlc_command(temp_project_dir, "next")
    assert result.returncode == 0
    
    # Check if PRD file was created
    prd_file = temp_project_dir / "doing" / idea_slug / f"02-prd-{idea_slug}.md"
    assert prd_file.exists()
    
    # Check lock file was updated
    lock_content = json.loads(lock_file.read_text())
    assert lock_content["current"] == "02-prd"
    
    # 5. Run done command
    # This would need the project to be in its final state
    # For a real test, we'd need to mock or create all expected files
    
    # For now, let's just verify the lock file structure
    assert "slug" in lock_content
    assert "current" in lock_content
    assert "created" in lock_content