"""Shared helpers."""

from __future__ import annotations

from pathlib import Path
import json
import re
import unicodedata

ROOT = Path.cwd()

# --- TOML loader (Python ≥3.11 stdlib) --------------------------------------
try:
    import tomllib as _toml  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover – fallback for < 3.11
    import tomli as _toml    # noqa: D401  # `uv pip install tomli`

ROOT = Path.cwd()  # repo root – we run CLI from here


def load_config() -> dict:
    cfg_path = ROOT / ".aisdlc"
    if not cfg_path.exists():
        raise FileNotFoundError(".aisdlc manifest missing – run `aisdlc init`.")
    return _toml.loads(cfg_path.read_text())


def slugify(text: str) -> str:
    """kebab-case ascii only"""
    slug = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()
    return slug or "idea"


def read_lock() -> dict:
    path = ROOT / ".aisdlc.lock"
    return json.loads(path.read_text()) if path.exists() else {}


def write_lock(data: dict) -> None:
    (ROOT / ".aisdlc.lock").write_text(json.dumps(data, indent=2))
