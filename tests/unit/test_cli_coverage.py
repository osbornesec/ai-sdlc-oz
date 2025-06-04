"""Additional tests for CLI module to achieve 100% coverage."""

from unittest.mock import patch

from ai_sdlc import cli


class TestCLICoverage:
    """Additional test cases for CLI coverage."""

    def test_display_compact_status_config_error(self, capsys):
        """Test _display_compact_status when config has issues."""
        lock = {'slug': 'test-feature', 'current': 'invalid-step'}
        config = {'steps': ['00-idea', '01-prd']}

        with patch('ai_sdlc.cli.read_lock', return_value=lock):
            with patch('ai_sdlc.cli.load_config', return_value=config):
                cli._display_compact_status()

        captured = capsys.readouterr()
        assert "Current: test-feature @ invalid-step (Step not in config)" in captured.out

    def test_display_compact_status_file_not_found(self, capsys):
        """Test _display_compact_status when config file is missing."""
        lock = {'slug': 'test-feature', 'current': '00-idea'}

        with patch('ai_sdlc.cli.read_lock', return_value=lock):
            with patch('ai_sdlc.cli.load_config', side_effect=FileNotFoundError):
                cli._display_compact_status()

        captured = capsys.readouterr()
        assert "AI-SDLC config (.aisdlc) not found" in captured.out

    def test_display_compact_status_unexpected_error(self, capsys):
        """Test _display_compact_status with unexpected error."""
        lock = {'slug': 'test-feature', 'current': '00-idea'}

        with patch('ai_sdlc.cli.read_lock', return_value=lock):
            with patch('ai_sdlc.cli.load_config', side_effect=Exception("Unexpected")):
                cli._display_compact_status()

        captured = capsys.readouterr()
        assert "Could not display current status due to an unexpected issue" in captured.out

