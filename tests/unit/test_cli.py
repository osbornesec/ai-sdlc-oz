"""Unit tests for the CLI module."""

import sys
from unittest.mock import Mock, patch

import pytest

from ai_sdlc import cli


class TestCLI:
    """Test cases for CLI functionality."""

    def test_main_no_args(self, capsys):
        """Test main function with no arguments shows help."""
        with patch.object(sys, "argv", ["aisdlc"]):
            with pytest.raises(SystemExit) as exc_info:
                cli.main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Usage: aisdlc" in captured.out

    def test_main_help_flag(self, capsys):
        """Test main function with help flag."""
        with patch.object(sys, "argv", ["aisdlc", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                cli.main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Usage: aisdlc" in captured.out

    def test_main_init_command(self):
        """Test main function with init command."""
        mock_init = Mock()
        with patch.object(sys, "argv", ["aisdlc", "init"]):
            with patch.dict("ai_sdlc.cli._COMMANDS", {"init": mock_init}):
                cli.main()
                mock_init.assert_called_once_with([])

    def test_main_new_command(self):
        """Test main function with new command."""
        mock_new = Mock()
        with patch.object(sys, "argv", ["aisdlc", "new", "Test Feature"]):
            with patch.dict("ai_sdlc.cli._COMMANDS", {"new": mock_new}):
                with patch(
                    "ai_sdlc.cli._display_compact_status"
                ):  # Mock status display
                    cli.main()
                    mock_new.assert_called_once_with(["Test Feature"])

    def test_main_next_command(self):
        """Test main function with next command."""
        mock_next = Mock()
        with patch.object(sys, "argv", ["aisdlc", "next"]):
            with patch.dict("ai_sdlc.cli._COMMANDS", {"next": mock_next}):
                with patch(
                    "ai_sdlc.cli._display_compact_status"
                ):  # Mock status display
                    cli.main()
                    mock_next.assert_called_once_with([])

    def test_main_status_command(self):
        """Test main function with status command."""
        mock_status = Mock()
        with patch.object(sys, "argv", ["aisdlc", "status"]):
            with patch.dict("ai_sdlc.cli._COMMANDS", {"status": mock_status}):
                cli.main()
                mock_status.assert_called_once_with([])

    def test_main_done_command(self):
        """Test main function with done command."""
        mock_done = Mock()
        with patch.object(sys, "argv", ["aisdlc", "done"]):
            with patch.dict("ai_sdlc.cli._COMMANDS", {"done": mock_done}):
                with patch(
                    "ai_sdlc.cli._display_compact_status"
                ):  # Mock status display
                    cli.main()
                    mock_done.assert_called_once_with([])

    def test_main_context_command(self):
        """Test main function with context command."""
        mock_context = Mock()
        with patch.object(sys, "argv", ["aisdlc", "context", "--libraries", "pytest"]):
            with patch.dict("ai_sdlc.cli._COMMANDS", {"context": mock_context}):
                with patch(
                    "ai_sdlc.cli._display_compact_status"
                ):  # Mock status display
                    cli.main()
                    mock_context.assert_called_once_with(["--libraries", "pytest"])

    def test_main_invalid_command(self, capsys):
        """Test main function with invalid command."""
        with patch.object(sys, "argv", ["aisdlc", "invalid"]):
            with pytest.raises(SystemExit) as exc_info:
                cli.main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Usage: aisdlc" in captured.out

    def test_main_keyboard_interrupt(self):
        """Test main function handles KeyboardInterrupt."""
        mock_init = Mock(side_effect=KeyboardInterrupt)
        with patch.object(sys, "argv", ["aisdlc", "init"]):
            with patch.dict("ai_sdlc.cli._COMMANDS", {"init": mock_init}):
                with pytest.raises(KeyboardInterrupt):
                    cli.main()  # Should raise KeyboardInterrupt

    def test_display_compact_status_no_lock(self, capsys):
        """Test _display_compact_status with no lock."""
        with patch("ai_sdlc.cli.read_lock", return_value={}):
            cli._display_compact_status()

        captured = capsys.readouterr()
        assert captured.out == ""  # Should print nothing when no lock

    def test_display_compact_status_with_lock(self, capsys):
        """Test _display_compact_status with active workstream."""
        lock = {"slug": "test-feature", "current": "01-prd"}
        config = {"steps": ["00-idea", "01-prd", "02-prd-plus"]}

        with patch("ai_sdlc.cli.read_lock", return_value=lock):
            with patch("ai_sdlc.cli.load_config", return_value=config):
                cli._display_compact_status()

        captured = capsys.readouterr()
        assert "Current: test-feature @ 01-prd" in captured.out
        assert "✅" in captured.out
        assert "☐" in captured.out
