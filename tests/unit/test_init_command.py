import os
from pathlib import Path

from ai_sdlc.commands import init


def test_run_init(temp_project_dir: Path, mocker):
    """Test init command creates actual files and directories."""
    # Patch ROOT to point to our temp directory
    mocker.patch("ai_sdlc.utils.ROOT", temp_project_dir)

    # Change to temp directory to simulate real usage
    original_cwd = os.getcwd()
    os.chdir(temp_project_dir)

    try:
        # Run the actual init command
        init.run_init()

        # Verify actual files/directories were created
        assert (temp_project_dir / ".aisdlc").exists(), ".aisdlc config file should exist"
        assert (temp_project_dir / "prompts").is_dir(), "prompts directory should exist"
        assert (temp_project_dir / "doing").is_dir(), "doing directory should exist"
        assert (temp_project_dir / "done").is_dir(), "done directory should exist"
        assert (temp_project_dir / ".aisdlc.lock").exists(), "lock file should exist"

        # Verify prompt files were created
        expected_prompts = [
            "00-idea.prompt.yml",
            "01-prd.prompt.yml",
            "02-prd-plus.prompt.yml",
            "03-system-template.prompt.yml",
            "04-systems-patterns.prompt.yml",
            "05-tasks.prompt.yml",
            "06-tasks-plus.prompt.yml",
            "07-tests.prompt.yml"
        ]

        for prompt_file in expected_prompts:
            prompt_path = temp_project_dir / "prompts" / prompt_file
            assert prompt_path.exists(), f"Prompt file {prompt_file} should exist"
            assert prompt_path.stat().st_size > 0, f"Prompt file {prompt_file} should not be empty"

        # Verify lock file content
        lock_content = (temp_project_dir / ".aisdlc.lock").read_text()
        assert lock_content.strip() == "{}", "Lock file should contain empty JSON object"

        # Verify .aisdlc config content has expected structure
        config_content = (temp_project_dir / ".aisdlc").read_text()
        assert "steps" in config_content, "Config should contain steps"
        assert "active_dir" in config_content, "Config should contain active_dir"
        assert "done_dir" in config_content, "Config should contain done_dir"

    finally:
        os.chdir(original_cwd)
