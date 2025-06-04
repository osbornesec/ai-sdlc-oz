"""Context7 integration service for enriching prompts with library documentation."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

import portalocker

from ..library_mappings import LIBRARY_MAPPINGS, LIBRARY_PATTERNS
from ..types import CacheEntry
from .context7_client import Context7Client

logger = logging.getLogger(__name__)


class Context7Service:
    """Service for integrating Context7 documentation into AI-SDLC workflow."""

    def __init__(self, cache_dir: Path):
        """Initialize Context7 service with cache directory."""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_index_file = self.cache_dir / "index.json"
        self.cache_lock_file = self.cache_dir / ".lock"
        self.cache_index = self._load_cache_index()
        self.client = Context7Client()

    def _acquire_lock(self, timeout: int = 10) -> None:
        """Acquire a file lock with a timeout."""
        self.cache_lock_file.touch(exist_ok=True)

        try:
            self._lock_handle = portalocker.Lock(
                self.cache_lock_file,
                mode="r+",
                timeout=timeout,
            )
            self._lock_handle.acquire()
        except portalocker.exceptions.LockException as e:
            raise TimeoutError("Could not acquire cache lock") from e

    def _release_lock(self) -> None:
        """Release the file lock."""
        try:
            if getattr(self, "_lock_handle", None) is not None:
                self._lock_handle.release()
                self._lock_handle = None
        except Exception as e:
            logger.warning(f"Error releasing lock: {e}")

    def _load_cache_index(self) -> dict[str, CacheEntry]:
        """Load cache index from disk with file locking."""
        if self.cache_index_file.exists():
            try:
                self._acquire_lock()
                try:
                    data = json.loads(self.cache_index_file.read_text())
                    return data
                except json.JSONDecodeError:
                    logger.warning("Cache index corrupted, resetting")
                    return {}
                finally:
                    self._release_lock()
            except TimeoutError:
                logger.warning("Could not acquire lock for reading cache index")
                return {}
        return {}

    def _save_cache_index(self) -> None:
        """Save cache index to disk with file locking."""
        try:
            self._acquire_lock()
            try:
                self.cache_index_file.write_text(json.dumps(self.cache_index, indent=2))
            finally:
                self._release_lock()
        except TimeoutError:
            logger.error("Could not acquire lock for saving cache index")

    def _is_cache_valid(self, cache_entry: CacheEntry) -> bool:
        """Check if cache entry is still valid (within 7 days)."""
        if "timestamp" not in cache_entry:
            return False
        cached_time = datetime.fromisoformat(cache_entry["timestamp"])
        return datetime.now() - cached_time < timedelta(days=7)

    def extract_libraries_from_text(self, text: str) -> list[str]:
        """Extract potential library/framework mentions from text."""
        libraries: set[str] = set()
        text_lower = text.lower()

        # Check for direct mentions of known libraries
        for variant, canonical in LIBRARY_MAPPINGS.items():
            # Use word boundaries to avoid partial matches
            if re.search(rf"\b{re.escape(variant)}\b", text_lower):
                libraries.add(canonical)

        # Look for common patterns using pre-compiled regexes
        for pattern in LIBRARY_PATTERNS:
            matches = pattern.findall(text_lower)
            for match in matches:
                if match in LIBRARY_MAPPINGS:
                    libraries.add(LIBRARY_MAPPINGS[match])

        return sorted(libraries)

    def _get_topic_for_step(self, step: str) -> str:
        """Get relevant topic focus for a specific step."""
        step_topics = {
            "3-system-template": "project structure, setup, configuration, getting started",
            "4-systems-patterns": "design patterns, architecture, best practices, advanced features",
            "5-tasks": "api reference, implementation, components, modules",
            "6-tasks-plus": "advanced features, optimization, performance, edge cases",
            "7-tests": "testing, test setup, mocking, test utilities",
        }
        return step_topics.get(step, "api reference, getting started, best practices")

    def get_step_specific_libraries(self, step: str) -> list[str]:
        """Get recommended libraries for a specific step."""
        step_libraries: dict[str, list[str]] = {
            "3-system-template": [
                "react",
                "vue",
                "angular",
                "fastapi",
                "django",
                "express",
            ],
            "4-systems-patterns": ["redux", "mobx", "sqlalchemy", "prisma"],
            "5-tasks": [],  # Dynamic based on previous steps
            "6-tasks-plus": [],  # Dynamic based on previous steps
            "7-tests": ["pytest", "jest", "vitest", "cypress", "mocha"],
        }
        return step_libraries.get(step, [])

    def format_library_docs_section(self, library_docs: dict[str, str]) -> str:
        """Format library documentation into a structured section."""
        if not library_docs:
            return ""

        sections = ["## Context7 Library Documentation\n"]
        sections.append(
            "*The following documentation has been fetched from Context7 to provide "
            "current, accurate information about the libraries mentioned in this project.*\n"
        )

        for library, docs in library_docs.items():
            sections.append(f"### {library.title()} Documentation\n")
            sections.append(docs)
            sections.append("")  # Empty line between libraries

        return "\n".join(sections)

    def enrich_prompt(
        self,
        prompt: str,
        step: str,
        previous_content: str,
        force_libraries: list[str] | None = None,
    ) -> str:
        """Enrich a prompt with relevant Context7 documentation."""
        # Extract libraries from previous content or use forced list
        if force_libraries:
            libraries = force_libraries
        else:
            libraries = self.extract_libraries_from_text(previous_content)

            # Add step-specific recommended libraries
            step_libraries = self.get_step_specific_libraries(step)
            for lib in step_libraries:
                if lib not in libraries and lib in previous_content.lower():
                    libraries.append(lib)

        if not libraries:
            return prompt

        # Placeholder for where actual Context7 MCP calls would happen
        library_docs: dict[str, str] = {}
        for library in libraries:
            # In real implementation, this would:
            # 1. Call resolve-library-id to get Context7 ID
            # 2. Call get-library-docs to fetch documentation
            # 3. Cache the results
            cache_key = f"{library}_{step}"

            if cache_key in self.cache_index and self._is_cache_valid(
                self.cache_index[cache_key]
            ):
                # Load from cache with locking
                cache_file = self.cache_dir / f"{cache_key}.md"
                if cache_file.exists():
                    try:
                        self._acquire_lock()
                        try:
                            library_docs[library] = cache_file.read_text()
                        finally:
                            self._release_lock()
                    except TimeoutError:
                        logger.warning(
                            f"Could not acquire lock for reading cache file: {cache_key}"
                        )
                        continue
            else:
                # Fetch from Context7 API
                library_id = self.client.resolve_library_id(library)
                if library_id:
                    # Get topic based on step
                    topic = self._get_topic_for_step(step)
                    docs = self.client.get_library_docs(
                        library_id, tokens=3000, topic=topic
                    )

                    if docs:
                        library_docs[library] = docs

                        # Cache the result with locking
                        cache_file = self.cache_dir / f"{cache_key}.md"
                        try:
                            self._acquire_lock()
                            try:
                                cache_file.write_text(docs)

                                cache_entry: CacheEntry = {
                                    "timestamp": datetime.now().isoformat(),
                                    "library_id": library_id,
                                }
                                self.cache_index[cache_key] = cache_entry
                                self._save_cache_index()
                                logger.debug(
                                    f"Cached documentation for {library} (ID: {library_id})"
                                )
                            finally:
                                self._release_lock()
                        except TimeoutError:
                            logger.error(
                                f"Could not acquire lock for caching docs: {cache_key}"
                            )
                    else:
                        library_docs[library] = (
                            f"<!-- Documentation not available for {library} -->"
                        )
                        logger.warning(
                            f"No documentation found for {library} (ID: {library_id})"
                        )
                else:
                    library_docs[library] = (
                        f"<!-- Could not resolve library: {library} -->"
                    )
                    logger.warning(f"Could not resolve library: {library}")

        # Find where to insert the documentation
        # Look for existing Context7 placeholder or insert before the first major heading
        context7_section = self.format_library_docs_section(library_docs)

        if "<context7_docs>" in prompt:
            # Replace placeholder
            prompt = prompt.replace("<context7_docs>", context7_section)
            prompt = prompt.replace("</context7_docs>", "")
        else:
            # Insert after initial description/title but before main content
            lines = prompt.split("\n")
            insert_index = 0

            # Find first major heading after initial content
            for i, line in enumerate(lines):
                if line.strip().startswith("##") and i > 2:
                    insert_index = i
                    break

            if insert_index > 0:
                lines.insert(insert_index, context7_section)
                prompt = "\n".join(lines)
            else:
                # Append at the end if no suitable location found
                prompt += f"\n\n{context7_section}"

        return prompt

    def create_context_command_output(
        self, step: str, detected_libraries: list[str]
    ) -> str:
        """Create formatted output for the context command."""
        output = []
        output.append(f"📚 Context7 Library Detection for Step: {step}")
        output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        if detected_libraries:
            output.append("\n🔍 Detected Libraries:")
            for lib in detected_libraries:
                output.append(f"  • {lib}")

            output.append(
                "\n💡 These libraries will be included in the next prompt generation."
            )
            output.append(
                "   Documentation will be fetched via Context7 MCP to provide:"
            )
            output.append("   - Current API references")
            output.append("   - Best practices and patterns")
            output.append("   - Version-specific information")
        else:
            output.append("\n❌ No libraries detected in the current content.")
            output.append("   You can manually specify libraries using:")
            output.append("   aisdlc context --libraries react,fastapi,postgresql")

        output.append(f"\n📁 Documentation cache location: {self.cache_dir}")

        return "\n".join(output)
