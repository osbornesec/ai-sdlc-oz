"""Final tests to achieve 100% code coverage."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_sdlc import cli, utils
from ai_sdlc.commands import context, init, new
from ai_sdlc.commands import next as next_cmd
from ai_sdlc.config_validator import ConfigValidationError


class TestFinalCoverage:
    """Final test cases to reach 100% coverage."""

    # CLI module - line 75 (main entry point)
    def test_cli_main_called_as_script(self):
        """Test cli.py when run as main module."""
        # We can't directly test the if __name__ == "__main__" block
        # but we can ensure it would work by testing main()
        with patch.object(cli.sys, 'argv', ['aisdlc', 'status']):
            mock_status = Mock()
            with patch.dict('ai_sdlc.cli._COMMANDS', {'status': mock_status}):
                cli.main()
                mock_status.assert_called_once()

    # Context command - uncovered lines
    def test_context_no_args_provided(self, temp_project_dir: Path, capsys):
        """Test context command with None args."""
        lock = {'slug': 'test-feature', 'current': '01-prd'}
        config = {'steps': ['00-idea', '01-prd'], 'context7': {'enabled': True}}

        # Create workdir
        workdir = temp_project_dir / 'doing' / 'test-feature'
        workdir.mkdir(parents=True)

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    with patch('ai_sdlc.commands.context.Context7Service') as mock_service:
                        instance = mock_service.return_value
                        instance.extract_libraries_from_text.return_value = []
                        instance.extract_libraries_for_step.return_value = []
                        instance.create_context_command_output.return_value = "Output"

                        context.run_context(None)  # Pass None for args

        captured = capsys.readouterr()
        assert "Output" in captured.out

    def test_context_library_name_too_long_after_strip(self, temp_project_dir: Path, capsys):
        """Test context with library name that's too long after stripping."""
        lock = {'slug': 'test', 'current': '01-prd'}
        config = {'steps': ['00-idea', '01-prd'], 'context7': {'enabled': True}}

        # Create a name that's exactly 50 chars after strip but longer with spaces
        long_name = ' ' + 'a' * 51 + ' '

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    with pytest.raises(SystemExit) as exc_info:
                        context.run_context(['--libraries', long_name])
                    assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Library name too long" in captured.out

    def test_context_show_cache_no_dir(self, temp_project_dir: Path, capsys):
        """Test --show-cache when cache dir doesn't exist."""
        lock = {'slug': 'test', 'current': '01-prd'}
        config = {'steps': ['00-idea', '01-prd'], 'context7': {'enabled': True}}

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    context.run_context(['--show-cache'])

        captured = capsys.readouterr()
        assert "Context7 cache location:" in captured.out
        assert "(empty)" in captured.out

    def test_context_clear_cache_permission_error(self, temp_project_dir: Path, capsys):
        """Test --clear-cache with permission error."""
        lock = {'slug': 'test', 'current': '01-prd'}
        config = {'steps': ['00-idea', '01-prd'], 'context7': {'enabled': True}}

        cache_dir = temp_project_dir / '.context7_cache'
        cache_dir.mkdir()

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    with patch('shutil.rmtree', side_effect=OSError("Permission denied")):
                        context.run_context(['--clear-cache'])

        captured = capsys.readouterr()
        assert "Error clearing cache" in captured.out
        assert "Permission denied" in captured.out

    def test_context_clear_cache_dir_not_exist(self, temp_project_dir: Path, capsys):
        """Test --clear-cache when dir doesn't exist."""
        lock = {'slug': 'test', 'current': '01-prd'}
        config = {'steps': ['00-idea', '01-prd'], 'context7': {'enabled': True}}

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    context.run_context(['--clear-cache'])

        captured = capsys.readouterr()
        assert "Cleared Context7 cache" in captured.out

    def test_context_missing_libraries_arg_value(self, temp_project_dir: Path, capsys):
        """Test context when --libraries flag has no value."""
        lock = {'slug': 'test', 'current': '01-prd'}
        config = {'steps': ['00-idea', '01-prd'], 'context7': {'enabled': True}}

        with patch('ai_sdlc.commands.context.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.context.load_config', return_value=config):
                with patch('ai_sdlc.commands.context.read_lock', return_value=lock):
                    with pytest.raises(SystemExit) as exc_info:
                        context.run_context(['--libraries'])  # No value after flag
                    assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error: --libraries requires a value" in captured.out

    def test_context_main_function(self):
        """Test context main() entry point."""
        with patch('ai_sdlc.commands.context.run_context') as mock_run:
            with patch('sys.argv', ['context.py', '--show-cache']):
                context.main()
                mock_run.assert_called_once_with(['--show-cache'])

    # Init command - uncovered lines
    def test_init_prompt_copy_oserror(self, temp_project_dir: Path, capsys):
        """Test init when prompt file copy fails with OSError."""
        with patch('ai_sdlc.commands.init.ROOT', temp_project_dir):
            # Create directories
            for dirname in ['prompts', 'doing', 'done']:
                (temp_project_dir / dirname).mkdir()

            # Create scaffold dir
            scaffold_dir = temp_project_dir / 'scaffold'
            scaffold_dir.mkdir()
            (scaffold_dir / '00-idea.prompt.yml').write_text('content')

            with patch('ai_sdlc.commands.init.SCAFFOLD_DIR', scaffold_dir):
                with patch('pathlib.Path.write_text') as mock_write:
                    # Allow config write, fail on prompt write
                    call_count = [0]
                    def side_effect(self, *args, **kwargs):
                        call_count[0] += 1
                        if call_count[0] > 1:  # First call is config, second is prompt
                            raise OSError("Disk full")
                        return None

                    mock_write.side_effect = side_effect
                    init.run_init([])

        captured = capsys.readouterr()
        assert "Error creating prompt" in captured.out
        assert "Disk full" in captured.out

    def test_init_not_all_prompts_exist(self, temp_project_dir: Path, capsys):
        """Test init when some prompts are missing."""
        with patch('ai_sdlc.commands.init.ROOT', temp_project_dir):
            # Create directories
            for dirname in ['prompts', 'doing', 'done']:
                (temp_project_dir / dirname).mkdir()

            # Create scaffold dir with only some files
            scaffold_dir = temp_project_dir / 'scaffold'
            scaffold_dir.mkdir()
            (scaffold_dir / '00-idea.prompt.yml').write_text('content')
            # Missing other prompt files

            with patch('ai_sdlc.commands.init.SCAFFOLD_DIR', scaffold_dir):
                init.run_init([])

        captured = capsys.readouterr()
        assert "Some prompt templates might be missing" in captured.out

    # New command - lines 56-57 (path traversal check)
    def test_new_path_resolution_error(self, temp_project_dir: Path, capsys):
        """Test new command when path resolution fails."""
        config = {'active_dir': 'doing', 'steps': ['00-idea']}

        with patch('ai_sdlc.commands.new.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.new.load_config', return_value=config):
                with patch('pathlib.Path.resolve', side_effect=Exception("Resolution failed")):
                    with pytest.raises(SystemExit) as exc_info:
                        new.run_new(['Test Feature'])
                    assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error validating path" in captured.out
        assert "Resolution failed" in captured.out

    # Next command - line 59 (step file reading)
    def test_next_read_previous_steps(self, temp_project_dir: Path):
        """Test next command reads all previous step files."""
        config = {
            'steps': ['00-idea', '01-prd', '02-prd-plus'],
            'active_dir': 'doing',
            'prompt_dir': 'prompts',
            'context7': {'enabled': True}
        }
        lock = {'slug': 'test-feature', 'current': '01-prd'}

        # Create files
        workdir = temp_project_dir / 'doing' / 'test-feature'
        workdir.mkdir(parents=True)
        (workdir / '00-idea-test-feature.md').write_text('Idea content')
        (workdir / '01-prd-test-feature.md').write_text('PRD content')

        prompt_dir = temp_project_dir / 'prompts'
        prompt_dir.mkdir()
        (prompt_dir / '02-prd-plus.prompt.yml').write_text('Prompt <prev_step></prev_step>')

        service_mock = Mock()
        service_mock.extract_libraries_from_text.return_value = []
        service_mock.enrich_prompt.return_value = "Enriched"

        with patch('ai_sdlc.commands.next.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.next.load_config', return_value=config):
                with patch('ai_sdlc.commands.next.read_lock', return_value=lock):
                    with patch('ai_sdlc.commands.next.Context7Service', return_value=service_mock):
                        next_cmd.run_next()

        # Verify all previous files were read
        service_mock.enrich_prompt.assert_called_once()
        call_args = service_mock.enrich_prompt.call_args[0]
        assert "Idea content" in call_args[2]  # combined_content arg
        assert "PRD content" in call_args[2]

    # Config validator - lines 104-105 (duplicate detection)
    def test_validate_duplicate_detection(self):
        """Test that config validator properly detects duplicates."""
        config = {
            'version': '0.1.0',
            'steps': ['00-idea', '01-prd', '00-idea'],  # Duplicate
            'active_dir': 'doing',
            'done_dir': 'done',
            'prompt_dir': 'prompts'
        }

        with pytest.raises(ConfigValidationError, match="Duplicate step found: 00-idea"):
            from ai_sdlc.config_validator import validate_config
            validate_config(config)

    # Utils - line 23 (unidecode import)
    def test_slugify_with_unicode(self):
        """Test slugify with unicode characters."""
        # Mock unidecode not being available
        import sys
        with patch.dict(sys.modules, {'unidecode': None}):
            # Clear the module cache
            if 'ai_sdlc.utils' in sys.modules:
                del sys.modules['ai_sdlc.utils']

            # Re-import to trigger the ImportError path
            from ai_sdlc import utils as utils_reload

            # Test with unicode - should still work with basic normalization
            result = utils_reload.slugify("Café Feature")
            assert result == "cafe-feature"

    # Utils - lines 60-63 (logger error in read_lock)
    def test_read_lock_json_decode_error(self, temp_project_dir: Path):
        """Test read_lock with JSON decode error."""
        lock_file = temp_project_dir / '.aisdlc.lock'
        lock_file.write_text('{invalid json')

        with patch('ai_sdlc.utils.LOCK', lock_file):
            with patch('ai_sdlc.utils.logger') as mock_logger:
                result = utils.read_lock()
                assert result == {}
                mock_logger.error.assert_called_once()
                assert "Error reading lock file" in str(mock_logger.error.call_args)
