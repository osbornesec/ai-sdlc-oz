"""Unit tests for the new command."""

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_sdlc.commands import new


class TestNewCommand:
    """Test cases for new command functionality."""

    def test_run_new_no_arguments(self, capsys):
        """Test new command with no arguments."""
        with pytest.raises(SystemExit) as exc_info:
            new.run_new([])
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert 'Usage: aisdlc new "Idea title"' in captured.out

    def test_run_new_directory_already_exists(self, temp_project_dir: Path, capsys):
        """Test new command when directory already exists."""
        config = {"active_dir": "doing", "steps": ["00-idea", "01-prd"]}

        # Create existing directory
        existing_dir = temp_project_dir / "doing" / "new-feature"
        existing_dir.mkdir(parents=True)

        with patch("ai_sdlc.commands.new.ROOT", temp_project_dir):
            with patch("ai_sdlc.commands.new.load_config", return_value=config):
                with pytest.raises(SystemExit) as exc_info:
                    new.run_new(["New Feature"])
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Work-stream 'new-feature' already exists." in captured.out

    def test_run_new_success(self, temp_project_dir: Path, capsys):
        """Test new command successfully creates a new feature."""
        config = {"active_dir": "doing", "steps": ["00-idea", "01-prd", "02-prd-plus"]}

        # Create doing directory
        doing_dir = temp_project_dir / "doing"
        doing_dir.mkdir()

        with patch("ai_sdlc.commands.new.ROOT", temp_project_dir):
            with patch("ai_sdlc.commands.new.load_config", return_value=config):
                with patch("ai_sdlc.commands.new.write_lock") as mock_write_lock:
                    new.run_new(["Test Feature"])

                    # Verify lock was written
                    assert mock_write_lock.called
                    lock_data = mock_write_lock.call_args[0][0]
                    assert lock_data["slug"] == "test-feature"
                    assert lock_data["current"] == "00-idea"

        captured = capsys.readouterr()
        assert "Created" in captured.out
        assert "00-idea-test-feature.md" in captured.out
        assert "Fill it out, then run `aisdlc next`" in captured.out

        # Verify directory and file were created
        feature_dir = doing_dir / "test-feature"
        assert feature_dir.exists()
        idea_file = feature_dir / "00-idea-test-feature.md"
        assert idea_file.exists()
        assert "# Test Feature" in idea_file.read_text()
        assert "## Problem" in idea_file.read_text()
        assert "## Solution" in idea_file.read_text()
        assert "## Rabbit Holes" in idea_file.read_text()

    def test_run_new_invalid_slug(self, temp_project_dir: Path, capsys):
        """Test new command with title that produces invalid slug."""
        config = {"active_dir": "doing", "steps": ["00-idea"]}

        with patch("ai_sdlc.commands.new.ROOT", temp_project_dir):
            with patch("ai_sdlc.commands.new.load_config", return_value=config):
                with patch(
                    "ai_sdlc.commands.new.slugify",
                    side_effect=ValueError("Invalid slug"),
                ):
                    with pytest.raises(SystemExit) as exc_info:
                        new.run_new(["!!!"])
                    assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.out
        assert "Idea title must contain alphanumeric characters" in captured.out

    def test_run_new_title_too_long(self, temp_project_dir: Path, capsys):
        """Test new command with title that's too long."""
        config = {"active_dir": "doing", "steps": ["00-idea"]}

        long_title = "A" * 201  # Over 200 char limit

        with patch("ai_sdlc.commands.new.ROOT", temp_project_dir):
            with patch("ai_sdlc.commands.new.load_config", return_value=config):
                with pytest.raises(SystemExit) as exc_info:
                    new.run_new([long_title])
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error: Idea title too long" in captured.out

    def test_run_new_title_too_short(self, temp_project_dir: Path, capsys):
        """Test new command with title that's too short."""
        config = {"active_dir": "doing", "steps": ["00-idea"]}

        with patch("ai_sdlc.commands.new.ROOT", temp_project_dir):
            with patch("ai_sdlc.commands.new.load_config", return_value=config):
                with pytest.raises(SystemExit) as exc_info:
                    new.run_new(["AB"])  # Under 3 char limit
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error: Idea title too short" in captured.out

    def test_run_new_os_error(self, temp_project_dir: Path, capsys):
        """Test new command when OS error occurs."""
        config = {"active_dir": "doing", "steps": ["00-idea"]}

        doing_dir = temp_project_dir / "doing"
        doing_dir.mkdir()

        with patch("ai_sdlc.commands.new.ROOT", temp_project_dir):
            with patch("ai_sdlc.commands.new.load_config", return_value=config):
                with patch(
                    "pathlib.Path.mkdir", side_effect=OSError("Permission denied")
                ):
                    with pytest.raises(SystemExit) as exc_info:
                        new.run_new(["Test Feature"])
                    assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error creating work-stream files" in captured.out
        assert "Permission denied" in captured.out

    def test_run_new_path_traversal_security(self, temp_project_dir: Path, capsys):
        """Test new command detects path traversal attempts."""
        config = {"active_dir": "doing", "steps": ["00-idea"]}

        with patch("ai_sdlc.commands.new.ROOT", temp_project_dir):
            with patch("ai_sdlc.commands.new.load_config", return_value=config):
                # Mock slugify to return a dangerous path
                with patch(
                    "ai_sdlc.commands.new.slugify", return_value="../../../etc/passwd"
                ):
                    with pytest.raises(SystemExit) as exc_info:
                        new.run_new(["Test"])
                    assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Security Error: Invalid path detected" in captured.out
