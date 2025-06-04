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
        if (
            context7_config is not None
        ):  # Ensure context7_config is not None before validation
            if not isinstance(context7_config, dict):
                errors.append("'context7' must be a dictionary")
            else:
                if "enabled" in context7_config:
                    if not isinstance(context7_config["enabled"], bool):
                        errors.append("'context7.enabled' must be a boolean")

    # Validate ai_provider config
    if "ai_provider" in config_data:
        ai_provider_config = config_data["ai_provider"]
        if not isinstance(ai_provider_config, dict):
            errors.append("'ai_provider' must be a dictionary")
        else:
            # Validate 'name'
            if "name" in ai_provider_config and not isinstance(
                ai_provider_config["name"], str
            ):
                errors.append("'ai_provider.name' must be a string")

            # Validate 'model'
            if "model" in ai_provider_config and not isinstance(
                ai_provider_config["model"], str
            ):
                errors.append("'ai_provider.model' must be a string")

            # Validate 'api_key_env_var'
            if "api_key_env_var" in ai_provider_config and not isinstance(
                ai_provider_config["api_key_env_var"], str
            ):
                errors.append("'ai_provider.api_key_env_var' must be a string")

            # Validate 'direct_api_calls'
            # This field is required if ai_provider section exists, defaults to False if section is missing (handled by get_default_config)
            # For newly created configs, get_default_config will set it.
            # For existing configs, if 'ai_provider' exists, 'direct_api_calls' should ideally be there.
            # However, to be lenient with potentially manually edited files that might miss this,
            # we can check its type if present, or rely on a default if truly absent inside an existing ai_provider dict.
            # The TypedDict with total=False allows it to be missing.
            # The prompt says "direct_api_calls (bool) is required if the section exists".
            # This implies if config_data has "ai_provider", then "direct_api_calls" must be in ai_provider_config.
            if "direct_api_calls" not in ai_provider_config:
                errors.append("'ai_provider.direct_api_calls' is required")
            elif not isinstance(ai_provider_config["direct_api_calls"], bool):
                errors.append("'ai_provider.direct_api_calls' must be a boolean")

            # Validate 'timeout_seconds'
            if "timeout_seconds" in ai_provider_config:
                timeout = ai_provider_config["timeout_seconds"]
                if not isinstance(timeout, int):
                    errors.append("'ai_provider.timeout_seconds' must be an integer")
                elif timeout <= 0:
                    errors.append(
                        "'ai_provider.timeout_seconds' must be a positive integer"
                    )
            # If timeout_seconds is not present, it will use the default from get_default_config or TypedDict default (if specified)
            # The requirement says "optional, defaults to 60". This default is handled by get_default_config.

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
        "ai_provider": {
            "name": "manual",
            "model": "",
            "api_key_env_var": "",
            "direct_api_calls": False,
            "timeout_seconds": 60,
        },
    }
