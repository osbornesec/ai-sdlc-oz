"""End-to-end integration tests for complete AI-SDLC workflows."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


class TestEndToEnd:
    """Test complete AI-SDLC workflows from start to finish."""

    @pytest.fixture
    def cli_runner(self, temp_project_dir: Path):
        """Create a CLI runner that executes in temp directory."""

        def run_command(cmd):
            """Run aisdlc command and return result."""
            result = subprocess.run(
                ["python", "-m", "ai_sdlc.cli"] + cmd.split()[1:],
                cwd=temp_project_dir,
                capture_output=True,
                text=True,
            )
            return result

        # Patch ROOT for all commands
        with patch("ai_sdlc.utils.ROOT", temp_project_dir):
            yield run_command

    def test_complete_feature_lifecycle(self, cli_runner, temp_project_dir: Path):
        """Test complete lifecycle from init to done."""
        # Step 1: Initialize project
        result = cli_runner("aisdlc init")
        assert result.returncode == 0
        assert (temp_project_dir / ".aisdlc").exists()
        assert (temp_project_dir / "doing").exists()
        assert (temp_project_dir / "done").exists()

        # Step 2: Create new feature
        result = cli_runner('aisdlc new "User Authentication System"')
        assert result.returncode == 0
        assert "✅  Created" in result.stdout
        assert "user-authentication-system" in result.stdout

        feature_dir = temp_project_dir / "doing" / "user-authentication-system"
        assert feature_dir.exists()

        # Step 3: Check status
        result = cli_runner("aisdlc status")
        assert result.returncode == 0
        assert "user-authentication-system" in result.stdout
        assert "00-idea" in result.stdout

        # Step 4: Progress through steps
        steps = [
            "00-idea",
            "01-prd",
            "02-prd-plus",
            "03-system-template",
            "04-systems-patterns",
            "05-tasks",
            "06-tasks-plus",
            "07-tests",
        ]

        for i in range(len(steps) - 1):
            next_step = steps[i + 1]

            # Run next command
            result = cli_runner("aisdlc next")
            assert result.returncode == 0

            # Simulate creating the next file
            next_file = feature_dir / f"{next_step}-user-authentication-system.md"
            next_file.write_text(
                f"# {next_step} Content\n\nGenerated content for {next_step}"
            )

            # Run next again to advance
            result = cli_runner("aisdlc next")
            assert result.returncode == 0
            assert f"Advanced to step: {next_step}" in result.stdout

        # Step 5: Complete the feature
        result = cli_runner("aisdlc done")
        assert result.returncode == 0
        assert "Archived to" in result.stdout

        # Verify feature was moved to done
        assert not feature_dir.exists()
        done_feature = temp_project_dir / "done" / "user-authentication-system"
        assert done_feature.exists()

        # Verify all files were moved
        for step in steps:
            assert (done_feature / f"{step}-user-authentication-system.md").exists()

    def test_context_integration(self, cli_runner, temp_project_dir: Path):
        """Test Context7 integration in workflow."""
        # Initialize and create feature
        cli_runner("aisdlc init")
        cli_runner('aisdlc new "FastAPI Microservice"')

        # Add content mentioning libraries
        feature_dir = temp_project_dir / "doing" / "fastapi-microservice"
        idea_file = feature_dir / "00-idea-fastapi-microservice.md"
        idea_file.write_text("""
# FastAPI Microservice

Building a microservice using FastAPI with pytest for testing,
SQLAlchemy for database, and Redis for caching.
""")

        # Test context detection
        result = cli_runner("aisdlc context")
        assert result.returncode == 0
        assert "Detected Libraries:" in result.stdout
        # Should detect mentioned libraries
        assert "fastapi" in result.stdout.lower() or "FastAPI" in result.stdout

        # Test forced libraries
        result = cli_runner("aisdlc context --libraries django,celery")
        assert result.returncode == 0
        assert "django" in result.stdout
        assert "celery" in result.stdout

        # Test cache operations
        result = cli_runner("aisdlc context --show-cache")
        assert result.returncode == 0

        result = cli_runner("aisdlc context --clear-cache")
        assert result.returncode == 0

    def test_multiple_features_workflow(self, cli_runner, temp_project_dir: Path):
        """Test handling multiple features."""
        cli_runner("aisdlc init")

        # Create first feature
        result = cli_runner('aisdlc new "Feature One"')
        assert result.returncode == 0

        # Create second feature (should succeed - multiple features allowed)
        result = cli_runner('aisdlc new "Feature Two"')
        assert result.returncode == 0

        # Verify both features exist
        feature_one_dir = temp_project_dir / "doing" / "feature-one"
        feature_two_dir = temp_project_dir / "doing" / "feature-two"
        assert feature_one_dir.exists()
        assert feature_two_dir.exists()

        # Complete first feature
        (feature_one_dir / "01-prd-feature-one.md").write_text("PRD content")
        cli_runner("aisdlc next")
        
        # Switch back to feature one to complete it
        # (Note: The lock now tracks feature-two, so we simulate switching back)
        # Create all required files and set to final step
        for step in ["00-idea", "01-prd", "02-prd-plus", "03-system-template", 
                     "04-systems-patterns", "05-tasks", "06-tasks-plus", "07-tests"]:
            step_file = feature_one_dir / f"{step}-feature-one.md"
            if not step_file.exists():
                step_file.write_text(f"# {step} content")
        
        lock_file = temp_project_dir / ".aisdlc.lock"
        lock_data = {
            "slug": "feature-one",
            "current": "07-tests",  # Set to last step to allow done
            "created": "2023-01-01T00:00:00"
        }
        import json
        lock_file.write_text(json.dumps(lock_data))
        
        result = cli_runner("aisdlc done")
        assert result.returncode == 0

    def test_error_handling_workflow(self, cli_runner, temp_project_dir: Path):
        """Test error handling in workflow."""
        # Try commands without init
        result = cli_runner('aisdlc new "Test"')
        assert result.returncode == 1
        assert ".aisdlc not found" in result.stdout

        # Initialize
        cli_runner("aisdlc init")

        # Try status without active feature
        result = cli_runner("aisdlc status")
        assert result.returncode == 0
        assert "none" in result.stdout or "No active workstream" in result.stdout

        # Try next without active feature
        result = cli_runner("aisdlc next")
        assert result.returncode == 1
        assert "No active workstream" in result.stdout

        # Try done without active feature
        result = cli_runner("aisdlc done")
        assert result.returncode == 1
        assert "No active workstream" in result.stdout

    def test_custom_configuration(self, cli_runner, temp_project_dir: Path):
        """Test workflow with custom configuration."""
        # Create custom config
        custom_config = """
version = "0.2.0"
steps = ["00-concept", "01-design", "02-implement"]
active_dir = "wip"
done_dir = "completed"
prompt_dir = "templates"

[context7]
enabled = false

[ai_provider]
name = "manual"
model = ""
api_key_env_var = ""
direct_api_calls = false
timeout_seconds = 60
"""
        (temp_project_dir / ".aisdlc").write_text(custom_config)

        # Create directories
        (temp_project_dir / "wip").mkdir()
        (temp_project_dir / "completed").mkdir()
        (temp_project_dir / "templates").mkdir()

        # Create empty lock
        (temp_project_dir / ".aisdlc.lock").write_text("{}")

        # Create prompt templates
        for step in ["00-concept", "01-design", "02-implement"]:
            template = temp_project_dir / "templates" / f"{step}.prompt.yml"
            template.write_text(f"# {step} template\n<prev_step></prev_step>")

        # Test with custom config
        result = cli_runner('aisdlc new "Custom Feature"')
        assert result.returncode == 0

        # Verify custom directories are used
        assert (temp_project_dir / "wip" / "custom-feature").exists()
        assert not (temp_project_dir / "doing" / "custom-feature").exists()

    @pytest.mark.parametrize(
        "invalid_title",
        [
            "",
            "   ",
            "!!!",
            "---",
            "@#$%^&*()",
        ],
    )
    def test_invalid_feature_titles(
        self, cli_runner, temp_project_dir: Path, invalid_title
    ):
        """Test handling of invalid feature titles."""
        cli_runner("aisdlc init")

        result = cli_runner(f'aisdlc new "{invalid_title}"')
        assert result.returncode == 1
        assert (
            "❌  Error:" in result.stdout
            or "❌  Error:" in result.stderr
        )

    def test_unicode_handling(self, cli_runner, temp_project_dir: Path):
        """Test handling of unicode in feature names."""
        cli_runner("aisdlc init")

        # Create feature with unicode
        result = cli_runner('aisdlc new "Café Management System"')
        assert result.returncode == 0
        assert "cafe-management-system" in result.stdout

        # Verify files are created correctly
        feature_dir = temp_project_dir / "doing" / "cafe-management-system"
        assert feature_dir.exists()

        idea_file = feature_dir / "00-idea-cafe-management-system.md"
        content = idea_file.read_text(encoding="utf-8")
        assert "Café Management System" in content
