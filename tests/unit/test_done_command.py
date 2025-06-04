"""Unit tests for the done command."""

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_sdlc.commands import done


class TestDoneCommand:
    """Test cases for done command functionality."""

    def test_run_done_no_active_workstream(self, temp_project_dir: Path, capsys):
        """Test done command when no active workstream exists."""
        with patch('ai_sdlc.commands.done.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.done.load_config', return_value={'active_dir': 'doing', 'done_dir': 'done', 'steps': ['00-idea', '01-prd', '02-prd-plus']}):
                with patch('ai_sdlc.commands.done.read_lock', return_value={}):
                    done.run_done()

        captured = capsys.readouterr()
        assert "No active workstream" in captured.out

    def test_run_done_success(self, temp_project_dir: Path, capsys):
        """Test done command successfully archives a feature."""
        # Setup test data
        config = {
            'active_dir': 'doing',
            'done_dir': 'done',
            'steps': ['00-idea', '01-prd', '02-prd-plus']
        }
        lock = {
            'slug': 'test-feature',
            'current': '02-prd-plus'
        }

        # Create test feature directory and files
        doing_dir = temp_project_dir / 'doing' / 'test-feature'
        doing_dir.mkdir(parents=True)
        (doing_dir / '00-idea-test-feature.md').write_text('Idea content')
        (doing_dir / '01-prd-test-feature.md').write_text('PRD content')
        (doing_dir / '02-prd-plus-test-feature.md').write_text('PRD+ content')

        # Create done directory
        done_dir = temp_project_dir / 'done'
        done_dir.mkdir()

        with patch('ai_sdlc.commands.done.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.done.load_config', return_value=config):
                with patch('ai_sdlc.commands.done.read_lock', return_value=lock):
                    with patch('ai_sdlc.commands.done.write_lock') as mock_write_lock:
                        done.run_done()

                        # Verify lock was cleared
                        mock_write_lock.assert_called_once_with({})

        captured = capsys.readouterr()
        assert "Archived to" in captured.out
        assert "test-feature" in captured.out

        # Verify files were moved
        assert not doing_dir.exists()
        archived_dir = done_dir / 'test-feature'
        assert archived_dir.exists()
        assert (archived_dir / '00-idea-test-feature.md').exists()
        assert (archived_dir / '01-prd-test-feature.md').exists()
        assert (archived_dir / '02-prd-plus-test-feature.md').exists()

    def test_run_done_not_finished(self, temp_project_dir: Path, capsys):
        """Test done command when workstream is not finished."""
        config = {
            'active_dir': 'doing',
            'done_dir': 'done',
            'steps': ['00-idea', '01-prd', '02-prd-plus']
        }
        lock = {
            'slug': 'unfinished-feature',
            'current': '01-prd'
        }

        # Create done directory but not the source
        done_dir = temp_project_dir / 'done'
        done_dir.mkdir()

        with patch('ai_sdlc.commands.done.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.done.load_config', return_value=config):
                with patch('ai_sdlc.commands.done.read_lock', return_value=lock):
                    done.run_done()

        captured = capsys.readouterr()
        assert "Workstream not finished yet" in captured.out

    def test_run_done_missing_files(self, temp_project_dir: Path, capsys):
        """Test done command when required files are missing."""
        config = {
            'active_dir': 'doing',
            'done_dir': 'done',
            'steps': ['00-idea', '01-prd', '02-prd-plus']
        }
        lock = {
            'slug': 'test-feature',
            'current': '02-prd-plus'
        }

        # Create source directory with missing files
        doing_dir = temp_project_dir / 'doing' / 'test-feature'
        doing_dir.mkdir(parents=True)
        (doing_dir / '00-idea-test-feature.md').write_text('Idea')
        # Missing 01-prd and 02-prd-plus files

        done_dir = temp_project_dir / 'done'
        done_dir.mkdir()

        with patch('ai_sdlc.commands.done.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.done.load_config', return_value=config):
                with patch('ai_sdlc.commands.done.read_lock', return_value=lock):
                    done.run_done()

        captured = capsys.readouterr()
        assert "Missing files:" in captured.out

    def test_run_done_move_error(self, temp_project_dir: Path, capsys):
        """Test done command when move operation fails."""
        config = {
            'active_dir': 'doing',
            'done_dir': 'done',
            'steps': ['00-idea', '01-prd', '02-prd-plus']
        }
        lock = {
            'slug': 'test-feature',
            'current': '02-prd-plus'
        }

        # Create source directory and files
        doing_dir = temp_project_dir / 'doing' / 'test-feature'
        doing_dir.mkdir(parents=True)
        (doing_dir / '00-idea-test-feature.md').write_text('Idea')
        (doing_dir / '01-prd-test-feature.md').write_text('PRD')
        (doing_dir / '02-prd-plus-test-feature.md').write_text('PRD+')

        done_dir = temp_project_dir / 'done'
        done_dir.mkdir()

        with patch('ai_sdlc.commands.done.ROOT', temp_project_dir):
            with patch('ai_sdlc.commands.done.load_config', return_value=config):
                with patch('ai_sdlc.commands.done.read_lock', return_value=lock):
                    with patch('shutil.move', side_effect=OSError("Permission denied")):
                        with pytest.raises(SystemExit) as exc_info:
                            done.run_done()
                        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error archiving work-stream" in captured.out
        assert "Permission denied" in captured.out
