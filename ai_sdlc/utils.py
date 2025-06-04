"""Shared helpers."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

from .config_validator import ConfigValidationError, validate_config
from .types import ConfigDict, LockDict


def find_project_root() -> Path:
    """Find project root by searching for .aisdlc file in current and parent directories."""
    current_dir = Path.cwd()
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / ".aisdlc").exists():
            return parent
    # For init command, return current directory if no .aisdlc found
    # Other commands will check for .aisdlc existence separately
    return current_dir


ROOT = find_project_root()

# --- TOML loader (Python ≥3.11 stdlib) --------------------------------------
try:
    import tomllib as toml_lib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover – fallback for < 3.11
    # `uv pip install tomli`
    import tomli as toml_lib  # noqa: D401  # pyright: ignore[reportMissingImports]


def load_config() -> ConfigDict:
    """Load and validate configuration from .aisdlc file.

    Returns:
        Parsed and validated configuration

    Raises:
        SystemExit: If config file is missing or corrupted
    """
    cfg_path = ROOT / ".aisdlc"
    if not cfg_path.exists():
        print(
            "Error: .aisdlc not found. Ensure you are in an ai-sdlc project directory."
        )
        print("Run `aisdlc init` to initialize a new project.")
        sys.exit(1)
    try:
        config_data = toml_lib.loads(cfg_path.read_text())
        # Validate configuration structure
        validated_config = validate_config(config_data)
        return validated_config
    except toml_lib.TOMLDecodeError as e:
        print(f"❌ Error: '.aisdlc' configuration file is corrupted: {e}")
        print("Please fix the .aisdlc file or run 'aisdlc init' in a new directory.")
        sys.exit(1)
    except ConfigValidationError as e:
        print(f"❌ Error: Invalid configuration: {e}")
        print("Please fix the .aisdlc file or run 'aisdlc init' in a new directory.")
        sys.exit(1)


def slugify(text: str) -> str:
    """Convert text to kebab-case ASCII slug.

    Args:
        text: Input text to convert to slug

    Returns:
        kebab-case ASCII slug

    Raises:
        ValueError: If text is empty or contains no valid characters
    """
    if not text or not text.strip():
        raise ValueError("Cannot slugify empty text")

    slug = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()

    if not slug:
        raise ValueError(f"Text '{text}' contains no valid characters for slug")

    return slug


def read_lock() -> LockDict:
    """Read and parse the lock file.

    Returns:
        Lock file data or empty dict if file doesn't exist or is corrupted
    """
    path = ROOT / ".aisdlc.lock"
    if not path.exists():
        return {}
    try:
        lock_data = json.loads(path.read_text())
        return lock_data
    except json.JSONDecodeError:
        print(
            "⚠️  Warning: '.aisdlc.lock' file is corrupted or not valid JSON. Treating as empty."
        )
        return {}


def write_lock(data: LockDict) -> None:
    """Write lock data to file.

    Args:
        data: Lock data to write
    """
    (ROOT / ".aisdlc.lock").write_text(json.dumps(data, indent=2))
