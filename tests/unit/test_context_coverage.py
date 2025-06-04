"""Additional tests for context command to achieve 100% coverage."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_sdlc.commands import context


class TestContextCoverage:
    """Additional test cases for context command coverage."""

    def test_run_context_with_existing_lock(self, temp_project_dir: Path, capsys):
        """Test context command with existing lock file."""
        lock = {'slug': 'test-feature', 'current': '01-prd'}
        config = {
            'steps': ['00-idea', '01-prd', '02-prd-plus'],
            'context7': {'enabled': True}
        }

        # Create test files
        feature_dir = temp_project_dir / 'doing' / 'test-feature'
        feature_dir.mkdir(parents=True)
        (feature_dir / '00-idea-test-feature.md').write_text('# Test Feature\nidea content')
        (feature_dir / '01-prd-test-feature.md').write_text('PRD content')

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    context.run_context(['--step', '01-prd'])

        captured = capsys.readouterr()
        assert "Context7 Library Detection" in captured.out

    def test_run_context_invalid_library_name(self, temp_project_dir: Path, capsys):
        """Test context command with invalid library name."""
        lock = {'slug': 'test-feature', 'current': '01-prd'}
        config = {'steps': ['00-idea', '01-prd'], 'context7': {'enabled': True}}

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    with pytest.raises(SystemExit) as exc_info:
                        context.run_context(['--libraries', 'invalid@library'])
                    assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Invalid library name: invalid@library" in captured.out

    def test_run_context_library_name_too_long(self, temp_project_dir: Path, capsys):
        """Test context command with library name too long."""
        lock = {'slug': 'test-feature', 'current': '01-prd'}
        config = {'steps': ['00-idea', '01-prd'], 'context7': {'enabled': True}}

        long_name = 'a' * 51  # Over 50 character limit

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    with pytest.raises(SystemExit) as exc_info:
                        context.run_context(['--libraries', long_name])
                    assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Library name too long" in captured.out

    def test_run_context_show_cache(self, temp_project_dir: Path, capsys):
        """Test context command with --show-cache."""
        lock = {'slug': 'test-feature', 'current': '01-prd'}
        config = {'steps': ['00-idea', '01-prd'], 'context7': {'enabled': True}}

        cache_dir = temp_project_dir / '.context7_cache'
        cache_dir.mkdir()

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    context.run_context(['--show-cache'])

        captured = capsys.readouterr()
        assert "Context7 cache location:" in captured.out

    def test_run_context_clear_cache(self, temp_project_dir: Path, capsys):
        """Test context command with --clear-cache."""
        lock = {'slug': 'test-feature', 'current': '01-prd'}
        config = {'steps': ['00-idea', '01-prd'], 'context7': {'enabled': True}}

        # Create cache directory with a file
        cache_dir = temp_project_dir / '.context7_cache'
        cache_dir.mkdir()
        (cache_dir / 'test.json').write_text('{}')

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    context.run_context(['--clear-cache'])

        captured = capsys.readouterr()
        assert "Cleared Context7 cache" in captured.out
        assert not (cache_dir / 'test.json').exists()

    def test_run_context_unknown_argument(self, temp_project_dir: Path, capsys):
        """Test context command with unknown argument."""
        lock = {'slug': 'test-feature', 'current': '01-prd'}
        config = {'steps': ['00-idea', '01-prd'], 'context7': {'enabled': True}}

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    with pytest.raises(SystemExit) as exc_info:
                        context.run_context(['--unknown'])
                    assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Unknown argument: --unknown" in captured.out

    def test_run_context_no_libraries_no_lock(self, temp_project_dir: Path, capsys):
        """Test context command with no libraries and no lock."""
        config = {
            'steps': ['00-idea', '01-prd'],
            'context7': {'enabled': True}
        }

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value={}):
                    context.run_context([])

        captured = capsys.readouterr()
        assert "No libraries specified" in captured.out

    def test_run_context_with_step_flag(self, temp_project_dir: Path, capsys):
        """Test context command with step flag."""
        config = {
            'steps': ['00-idea', '01-prd', '02-prd-plus'],
            'context7': {'enabled': True}
        }

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value={}):
                    context.run_context(['--step', '02-prd-plus'])

        captured = capsys.readouterr()
        assert "Context7 Library Detection for Step: 02-prd-plus" in captured.out

    def test_get_context_command_libraries_specified(self, temp_project_dir: Path, capsys):
        """Test context with specified libraries."""
        config = {
            'steps': ['00-idea', '01-prd'],
            'context7': {'enabled': True}
        }

        service_mock = Mock()
        service_mock.extract_libraries_for_step.return_value = []
        service_mock.create_context_command_output.return_value = "Test output"

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.Context7Service', return_value=service_mock):
                    context.run_context(['--libraries', 'httpx,pytest'])

        captured = capsys.readouterr()
        assert "Test output" in captured.out
        service_mock.create_context_command_output.assert_called_once_with(
            ['httpx', 'pytest'],
            current_step=None,
            step_recommendations={}
        )

    def test_run_context_cache_dir_creation(self, temp_project_dir: Path):
        """Test that cache directory is created properly."""
        config = {
            'steps': ['00-idea'],
            'context7': {'enabled': True}
        }

        cache_dir = temp_project_dir / '.context7_cache'

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.Context7Service') as service_mock:
                    context.run_context(['--libraries', 'test'])

        # Verify Context7Service was initialized with cache_dir
        service_mock.assert_called_once_with(cache_dir)
