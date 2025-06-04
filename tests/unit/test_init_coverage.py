"""Additional tests for init command to achieve 100% coverage."""

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_sdlc.commands import init


class TestInitCoverage:
    """Additional test cases for init command coverage."""

    def test_init_with_existing_config_file(self, temp_project_dir: Path, capsys):
        """Test init when config file already exists."""
        # Create existing config file
        config_file = temp_project_dir / ".aisdlc"
        config_file.write_text('{"version": "0.1.0"}')

        with patch("ai_sdlc.commands.init.ROOT", temp_project_dir):
            init.run_init([])

        captured = capsys.readouterr()
        assert "Config file .aisdlc already exists, skipping creation" in captured.out

    def test_init_directory_creation_error(self, temp_project_dir: Path, capsys):
        """Test init when directory creation fails."""
        with patch("ai_sdlc.commands.init.ROOT", temp_project_dir):
            with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
                with pytest.raises(SystemExit) as exc_info:
                    init.run_init([])
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error creating directories" in captured.out
        assert "Permission denied" in captured.out

    def test_init_config_write_error(self, temp_project_dir: Path, capsys):
        """Test init when config file write fails."""
        with patch("ai_sdlc.commands.init.ROOT", temp_project_dir):
            # Make directories succeed
            for dirname in ["prompts", "doing", "done"]:
                (temp_project_dir / dirname).mkdir()

            with patch("pathlib.Path.write_text", side_effect=OSError("Disk full")):
                with pytest.raises(SystemExit) as exc_info:
                    init.run_init([])
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error writing config file" in captured.out
        assert "Disk full" in captured.out

    def test_init_prompt_file_not_found(self, temp_project_dir: Path, capsys):
        """Test init when prompt files are not found in package."""
        with patch("ai_sdlc.commands.init.ROOT", temp_project_dir):
            # Create directories
            for dirname in ["prompts", "doing", "done"]:
                (temp_project_dir / dirname).mkdir()

            # Mock the scaffold directory to not have files
            empty_dir = temp_project_dir / "empty_scaffold"
            empty_dir.mkdir()

            with patch("ai_sdlc.commands.init.SCAFFOLD_DIR", empty_dir):
                init.run_init([])

        captured = capsys.readouterr()
        assert "Warning: Packaged prompt template" in captured.out
        assert "not found within ai-sdlc package" in captured.out

    def test_init_lock_file_write_error(self, temp_project_dir: Path, capsys):
        """Test init when lock file write fails."""
        with patch("ai_sdlc.commands.init.ROOT", temp_project_dir):
            # Create directories
            for dirname in ["prompts", "doing", "done"]:
                (temp_project_dir / dirname).mkdir()

            # Create config
            config_file = temp_project_dir / ".aisdlc"
            config_file.write_text('{"version": "0.1.0"}')

            # Create scaffold dir
            scaffold_dir = temp_project_dir / "scaffold"
            scaffold_dir.mkdir()
            for i in range(8):
                (scaffold_dir / f"0{i}-test.prompt.yml").write_text("test")

            with patch("ai_sdlc.commands.init.SCAFFOLD_DIR", scaffold_dir):
                # Make lock file write fail
                with patch("pathlib.Path.write_text") as mock_write:
                    # Allow config write, fail on lock write
                    def side_effect(self, *args, **kwargs):
                        if self.name == ".aisdlc.lock":
                            raise OSError("Cannot write lock")
                        return None

                    mock_write.side_effect = side_effect

                    with pytest.raises(SystemExit) as exc_info:
                        init.run_init([])
                    assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error writing lock file" in captured.out
