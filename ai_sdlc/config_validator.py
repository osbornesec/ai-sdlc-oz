"""Configuration validation for AI-SDLC."""

from __future__ import annotations

from typing import Any

from .types import ConfigDict


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


def validate_config(config_data: dict[str, Any]) -> ConfigDict:
    """Validate configuration data structure and values.

    Args:
        config_data: Raw configuration data from TOML file

    Returns:
        Validated configuration

    Raises:
        ConfigValidationError: If configuration is invalid
    """
    errors = []

    # Check required fields
    required_fields = ["version", "steps", "active_dir", "done_dir", "prompt_dir"]
    for field in required_fields:
        if field not in config_data:
            errors.append(f"Missing required field: {field}")

    # Validate version
    if "version" in config_data:
        if not isinstance(config_data["version"], str):
            errors.append("'version' must be a string")
        elif not config_data["version"].strip():
            errors.append("'version' cannot be empty")

    # Validate steps
    if "steps" in config_data:
        steps = config_data["steps"]
        if not isinstance(steps, list):
            errors.append("'steps' must be a list")
        elif not steps:
            errors.append("'steps' cannot be empty")
        else:
            for i, step in enumerate(steps):
                if not isinstance(step, str):
                    errors.append(f"Step {i} must be a string")
                elif not step.strip():
                    errors.append(f"Step {i} cannot be empty")
                elif not step.startswith(f"{i:02d}-"):
                    errors.append(
                        f"Step {i} must start with '{i:02d}-' (got: '{step}')"
                    )

    # Validate directory fields
    dir_fields = ["active_dir", "done_dir", "prompt_dir"]
    for field in dir_fields:
        if field in config_data:
            value = config_data[field]
            if not isinstance(value, str):
                errors.append(f"'{field}' must be a string")
            elif not value.strip():
                errors.append(f"'{field}' cannot be empty")
            elif "/" in value or "\\" in value:
                errors.append(
                    f"'{field}' must be a simple directory name (no path separators)"
                )

    # Validate context7 config if present
    if "context7" in config_data:
        context7_config = config_data["context7"]
        if not isinstance(context7_config, dict):
            errors.append("'context7' must be a dictionary")
        else:
            if "enabled" in context7_config:
                if not isinstance(context7_config["enabled"], bool):
                    errors.append("'context7.enabled' must be a boolean")

    if errors:
        raise ConfigValidationError("; ".join(errors))

    return config_data  # type: ignore[return-value]


def validate_steps_sequence(steps: list[str]) -> None:
    """Validate that steps are in correct sequence.

    Args:
        steps: List of step names

    Raises:
        ConfigValidationError: If steps are not in correct sequence
    """
    for i, step in enumerate(steps):
        expected_prefix = f"{i:02d}-"
        if not step.startswith(expected_prefix):
            raise ConfigValidationError(
                f"Step {i} should start with '{expected_prefix}', got: '{step}'"
            )

    # Check for duplicates
    if len(set(steps)) != len(steps):
        duplicates = [step for step in set(steps) if steps.count(step) > 1]
        raise ConfigValidationError(f"Duplicate steps found: {duplicates}")


def get_default_config() -> ConfigDict:
    """Get default configuration structure.

    Returns:
        Default configuration
    """
    return {
        "version": "0.7.0-dev",
        "steps": [
            "00-idea",
            "01-prd",
            "02-prd-plus",
            "03-system-template",
            "04-systems-patterns",
            "05-tasks",
            "06-tasks-plus",
            "07-tests",
        ],
        "active_dir": "doing",
        "done_dir": "done",
        "prompt_dir": "prompts",
        "context7": {"enabled": True},
    }
