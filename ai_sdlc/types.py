"""Type definitions for AI-SDLC."""

from __future__ import annotations

from typing import TypedDict


class ConfigDict(TypedDict):
    """Configuration structure for .aisdlc file."""

    version: str
    steps: list[str]
    active_dir: str
    done_dir: str
    prompt_dir: str
    context7: Context7ConfigDict | None


class Context7ConfigDict(TypedDict, total=False):
    """Context7 configuration structure."""

    enabled: bool


class LockDict(TypedDict, total=False):
    """Lock file structure for .aisdlc.lock."""

    slug: str
    current: str
    created: str


class LibraryResult(TypedDict, total=False):
    """Library result from Context7 API."""

    name: str
    libraryId: str
    description: str
    codeSnippetCount: int
    trustScore: float


class CacheEntry(TypedDict):
    """Cache entry structure."""

    timestamp: str
    library_id: str
