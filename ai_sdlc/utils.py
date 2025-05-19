"""Shared helpers."""

from __future__ import annotations

from pathlib import Path
import json
import re
import sys
import unicodedata

def find_project_root() -> Path:
    """Find project root by searching for .aisdlc file in current and parent directories."""
    current_dir = Path.cwd()
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / ".aisdlc").exists():
            return parent
    # Fallback or error
    print("Error: .aisdlc not found. Ensure you are in an ai-sdlc project directory.")
    sys.exit(1)

ROOT = find_project_root()

# --- TOML loader (Python ≥3.11 stdlib) --------------------------------------
try:
    import tomllib as _toml  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover – fallback for < 3.11
    import tomli as _toml    # noqa: D401  # `uv pip install tomli`


def load_config() -> dict:
    cfg_path = ROOT / ".aisdlc"
    if not cfg_path.exists():
        raise FileNotFoundError(".aisdlc manifest missing – run `aisdlc init`.")
    try:
        return _toml.loads(cfg_path.read_text())
    except _toml.TOMLDecodeError as e:
        print(f"❌ Error: '.aisdlc' configuration file is corrupted: {e}")
        print("Please fix the .aisdlc file or run 'aisdlc init' in a new directory.")
        import sys
        sys.exit(1)


def slugify(text: str) -> str:
    """kebab-case ascii only"""
    slug = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()
    return slug or "idea"


def read_lock() -> dict:
    path = ROOT / ".aisdlc.lock"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        print("⚠️  Warning: '.aisdlc.lock' file is corrupted or not valid JSON. Treating as empty.")
        return {}


def write_lock(data: dict) -> None:
    (ROOT / ".aisdlc.lock").write_text(json.dumps(data, indent=2))
