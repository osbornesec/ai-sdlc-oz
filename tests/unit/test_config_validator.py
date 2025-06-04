"""Unit tests for the config validator."""

import pytest

from ai_sdlc.config_validator import (
    ConfigValidationError,
    get_default_config,
    validate_config,
    validate_steps_sequence,
)


class TestConfigValidator:
    """Test cases for config validation functionality."""

    def test_validate_config_success(self):
        """Test successful config validation."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea", "01-prd", "02-prd-plus"],
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        result = validate_config(config)
        assert result == config

    def test_validate_config_missing_version(self):
        """Test validation with missing version."""
        config = {
            "steps": ["00-idea"],
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(
            ConfigValidationError, match="Missing required field: version"
        ):
            validate_config(config)

    def test_validate_config_invalid_version_type(self):
        """Test validation with invalid version type."""
        config = {
            "version": 123,  # Should be string
            "steps": ["00-idea"],
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(ConfigValidationError, match="'version' must be a string"):
            validate_config(config)

    def test_validate_config_empty_version(self):
        """Test validation with empty version."""
        config = {
            "version": "  ",
            "steps": ["00-idea"],
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(ConfigValidationError, match="'version' cannot be empty"):
            validate_config(config)

    def test_validate_config_missing_steps(self):
        """Test validation with missing steps."""
        config = {
            "version": "0.1.0",
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(
            ConfigValidationError, match="Missing required field: steps"
        ):
            validate_config(config)

    def test_validate_config_empty_steps(self):
        """Test validation with empty steps list."""
        config = {
            "version": "0.1.0",
            "steps": [],
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(ConfigValidationError, match="'steps' cannot be empty"):
            validate_config(config)

    def test_validate_config_invalid_steps_type(self):
        """Test validation with invalid steps type."""
        config = {
            "version": "0.1.0",
            "steps": "not-a-list",
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(ConfigValidationError, match="'steps' must be a list"):
            validate_config(config)

    def test_validate_config_non_string_step(self):
        """Test validation with non-string step."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea", 123],
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(ConfigValidationError, match="Step 1 must be a string"):
            validate_config(config)

    def test_validate_config_empty_step(self):
        """Test validation with empty step."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea", "  "],
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(ConfigValidationError, match="Step 1 cannot be empty"):
            validate_config(config)

    def test_validate_config_invalid_step_format(self):
        """Test validation with invalid step format."""
        config = {
            "version": "0.1.0",
            "steps": ["0-idea", "01-prd"],  # First one missing zero-padding
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(ConfigValidationError, match="Step 0 must start with '00-'"):
            validate_config(config)

    def test_validate_config_missing_active_dir(self):
        """Test validation with missing active_dir."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea"],
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(
            ConfigValidationError, match="Missing required field: active_dir"
        ):
            validate_config(config)

    def test_validate_config_missing_done_dir(self):
        """Test validation with missing done_dir."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea"],
            "active_dir": "doing",
            "prompt_dir": "prompts",
        }

        with pytest.raises(
            ConfigValidationError, match="Missing required field: done_dir"
        ):
            validate_config(config)

    def test_validate_config_missing_prompt_dir(self):
        """Test validation with missing prompt_dir."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea"],
            "active_dir": "doing",
            "done_dir": "done",
        }

        with pytest.raises(
            ConfigValidationError, match="Missing required field: prompt_dir"
        ):
            validate_config(config)

    def test_validate_config_invalid_dir_type(self):
        """Test validation with invalid directory type."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea"],
            "active_dir": 123,  # Should be string
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(
            ConfigValidationError, match="'active_dir' must be a string"
        ):
            validate_config(config)

    def test_validate_config_empty_dir(self):
        """Test validation with empty directory."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea"],
            "active_dir": "   ",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(ConfigValidationError, match="'active_dir' cannot be empty"):
            validate_config(config)

    def test_validate_config_dir_with_path_separator(self):
        """Test validation with directory containing path separator."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea"],
            "active_dir": "path/to/dir",
            "done_dir": "done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(
            ConfigValidationError, match="'active_dir' must be a simple directory name"
        ):
            validate_config(config)

    def test_validate_config_dir_with_backslash(self):
        """Test validation with directory containing backslash."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea"],
            "active_dir": "doing",
            "done_dir": "path\\to\\done",
            "prompt_dir": "prompts",
        }

        with pytest.raises(
            ConfigValidationError, match="'done_dir' must be a simple directory name"
        ):
            validate_config(config)

    def test_validate_config_with_context7(self):
        """Test validation with context7 config."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea"],
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
            "context7": {"enabled": True},
        }

        result = validate_config(config)
        assert result["context7"]["enabled"] is True

    def test_validate_config_invalid_context7_type(self):
        """Test validation with invalid context7 type."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea"],
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
            "context7": "not-a-dict",
        }

        with pytest.raises(
            ConfigValidationError, match="'context7' must be a dictionary"
        ):
            validate_config(config)

    def test_validate_config_invalid_context7_enabled(self):
        """Test validation with invalid context7.enabled type."""
        config = {
            "version": "0.1.0",
            "steps": ["00-idea"],
            "active_dir": "doing",
            "done_dir": "done",
            "prompt_dir": "prompts",
            "context7": {
                "enabled": "yes"  # Should be boolean
            },
        }

        with pytest.raises(
            ConfigValidationError, match="'context7.enabled' must be a boolean"
        ):
            validate_config(config)

    def test_validate_config_multiple_errors(self):
        """Test validation with multiple errors."""
        config = {"steps": "not-a-list", "active_dir": 123}

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config(config)

        error_msg = str(exc_info.value)
        assert "Missing required field: version" in error_msg
        assert "'steps' must be a list" in error_msg
        assert "'active_dir' must be a string" in error_msg

    def test_validate_steps_sequence_success(self):
        """Test successful steps sequence validation."""
        steps = ["00-idea", "01-prd", "02-prd-plus", "03-design"]
        # Should not raise
        validate_steps_sequence(steps)

    def test_validate_steps_sequence_wrong_prefix(self):
        """Test steps sequence validation with wrong prefix."""
        steps = ["00-idea", "1-prd", "02-design"]

        with pytest.raises(
            ConfigValidationError, match="Step 1 should start with '01-'"
        ):
            validate_steps_sequence(steps)

    def test_validate_steps_sequence_non_sequential(self):
        """Test steps sequence validation with non-sequential steps."""
        steps = ["00-idea", "02-prd"]  # Missing 01

        with pytest.raises(
            ConfigValidationError, match="Step 1 should start with '01-'"
        ):
            validate_steps_sequence(steps)

    def test_validate_steps_sequence_duplicates(self):
        """Test steps sequence validation with duplicates."""
        steps = ["00-idea", "01-prd", "01-prd"]

        with pytest.raises(
            ConfigValidationError, match="Step 2 should start with '02-'"
        ):
            validate_steps_sequence(steps)

    def test_get_default_config(self):
        """Test getting default configuration."""
        config = get_default_config()

        assert config["version"] == "0.7.0-dev"
        assert len(config["steps"]) == 8
        assert config["steps"][0] == "00-idea"
        assert config["steps"][-1] == "07-tests"
        assert config["active_dir"] == "doing"
        assert config["done_dir"] == "done"
        assert config["prompt_dir"] == "prompts"
        assert config["context7"]["enabled"] is True
