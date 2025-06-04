"""Unit tests for the status command."""

from pathlib import Path
from unittest.mock import patch

from ai_sdlc.commands import status


class TestStatusCommand:
    """Test cases for status command functionality."""

    def test_run_status_no_active_workstream(self, temp_project_dir: Path, capsys):
        """Test status command when no active workstream exists."""
        with patch(
            "ai_sdlc.commands.status.load_config",
            return_value={"active_dir": "doing", "steps": ["00-idea", "01-prd"]},
        ):
            with patch("ai_sdlc.commands.status.read_lock", return_value={}):
                status.run_status()

        captured = capsys.readouterr()
        assert "Active workstreams" in captured.out
        assert "none – create one with `aisdlc new`" in captured.out

    def test_run_status_with_active_workstream(self, temp_project_dir: Path, capsys):
        """Test status command with an active workstream."""
        # Setup test data
        config = {"active_dir": "doing", "steps": ["00-idea", "01-prd", "02-prd-plus"]}
        lock = {"slug": "test-feature", "current": "01-prd"}

        # Create test files
        feature_dir = temp_project_dir / "doing" / "test-feature"
        feature_dir.mkdir(parents=True)
        (feature_dir / "00-idea-test-feature.md").write_text("Idea content")
        (feature_dir / "01-prd-test-feature.md").write_text("PRD content")

        with patch("ai_sdlc.commands.status.load_config", return_value=config):
            with patch("ai_sdlc.commands.status.read_lock", return_value=lock):
                status.run_status()

        captured = capsys.readouterr()
        assert "test-feature" in captured.out
        assert "01-prd" in captured.out
        assert "✅" in captured.out  # Completed steps
        assert "☐" in captured.out  # Pending steps

    def test_run_status_all_steps_complete(self, temp_project_dir: Path, capsys):
        """Test status command when all steps are complete."""
        config = {"active_dir": "doing", "steps": ["00-idea", "01-prd"]}
        lock = {"slug": "test-feature", "current": "01-prd"}

        # Create all files
        feature_dir = temp_project_dir / "doing" / "test-feature"
        feature_dir.mkdir(parents=True)
        (feature_dir / "00-idea-test-feature.md").write_text("Idea")
        (feature_dir / "01-prd-test-feature.md").write_text("PRD")

        with patch("ai_sdlc.commands.status.load_config", return_value=config):
            with patch("ai_sdlc.commands.status.read_lock", return_value=lock):
                status.run_status()

        captured = capsys.readouterr()
        assert "test-feature" in captured.out
        assert "01-prd" in captured.out
        assert "✅" in captured.out
        assert "☐" not in captured.out  # No pending steps
