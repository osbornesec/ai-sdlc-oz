"""Additional tests for utils module to achieve 100% coverage."""

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_sdlc import utils


class TestUtilsCoverage:
    """Additional test cases for utils module coverage."""

    def test_slugify_edge_cases(self):
        """Test slugify with various edge cases."""
        # Test with multiple spaces and special chars
        assert utils.slugify("  Hello   World!!!  ") == "hello-world"

        # Test with only special characters should raise ValueError
        with pytest.raises(ValueError, match="empty"):
            utils.slugify("!!!!!!")

        # Test with numbers
        assert utils.slugify("Version 2.0 Release") == "version-2-0-release"

        # Test with mixed case and underscores
        assert utils.slugify("My_Test__Feature") == "my-test-feature"

    def test_read_lock_missing_file(self, temp_project_dir: Path):
        """Test read_lock when file doesn't exist."""
        with patch('ai_sdlc.utils.LOCK', temp_project_dir / 'missing.lock'):
            result = utils.read_lock()
            assert result == {}

    def test_read_lock_invalid_json(self, temp_project_dir: Path):
        """Test read_lock with invalid JSON."""
        lock_file = temp_project_dir / 'test.lock'
        lock_file.write_text('invalid json content')

        with patch('ai_sdlc.utils.LOCK', lock_file):
            with patch('ai_sdlc.utils.logger') as mock_logger:
                result = utils.read_lock()
                assert result == {}
                mock_logger.error.assert_called_once()

    def test_write_lock_error(self, temp_project_dir: Path):
        """Test write_lock with write error."""
        lock_file = temp_project_dir / 'test.lock'

        with patch('ai_sdlc.utils.LOCK', lock_file):
            with patch('pathlib.Path.write_text', side_effect=OSError("Permission denied")):
                with pytest.raises(OSError, match="Permission denied"):
                    utils.write_lock({'test': 'data'})

    def test_load_config_with_context7_section(self, temp_project_dir: Path):
        """Test load_config with context7 configuration."""
        config_file = temp_project_dir / '.aisdlc'
        config_data = {
            'version': '0.1.0',
            'steps': ['00-idea'],
            'active_dir': 'doing',
            'done_dir': 'done',
            'prompt_dir': 'prompts',
            'context7': {
                'enabled': True,
                'cache_ttl': 3600
            }
        }
        config_file.write_text(utils.json.dumps(config_data))

        with patch('ai_sdlc.utils.CONFIG', config_file):
            result = utils.load_config()
            assert result['context7']['enabled'] is True
            assert result['context7']['cache_ttl'] == 3600

    def test_root_path_resolution(self):
        """Test ROOT path is properly resolved."""
        # ROOT should be an absolute path
        assert utils.ROOT.is_absolute()

        # Test that it can be used to create paths
        test_path = utils.ROOT / 'test'
        assert str(test_path).endswith('test')
