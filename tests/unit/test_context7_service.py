"""Unit tests for Context7 service."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_sdlc.services.context7_service import Context7Service, LIBRARY_MAPPINGS


class TestContext7Service:
    """Test Context7Service functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def service(self, temp_cache_dir):
        """Create a Context7Service instance with temp cache."""
        return Context7Service(temp_cache_dir)

    def test_init_creates_cache_dir(self, temp_cache_dir):
        """Test that initialization creates cache directory."""
        cache_dir = temp_cache_dir / "test_cache"
        assert not cache_dir.exists()
        
        service = Context7Service(cache_dir)
        assert cache_dir.exists()

    def test_extract_libraries_from_text(self, service):
        """Test library extraction from text."""
        text = """
        We're building a web app using React and FastAPI.
        The database is PostgreSQL and we're using Redux for state management.
        Testing is done with pytest and jest.
        """
        
        libraries = service.extract_libraries_from_text(text)
        
        assert "react" in libraries
        assert "fastapi" in libraries
        assert "postgresql" in libraries
        assert "redux" in libraries
        assert "pytest" in libraries
        assert "jest" in libraries

    def test_extract_libraries_with_variants(self, service):
        """Test library extraction handles variants."""
        text = "Using ReactJS with Express.js and MongoDB"
        
        libraries = service.extract_libraries_from_text(text)
        
        assert "react" in libraries  # ReactJS -> react
        assert "express" in libraries  # Express.js -> express
        assert "mongodb" in libraries  # MongoDB -> mongodb

    def test_extract_libraries_case_insensitive(self, service):
        """Test library extraction is case insensitive."""
        text = "REACT and DJANGO with MYSQL"
        
        libraries = service.extract_libraries_from_text(text)
        
        assert "react" in libraries
        assert "django" in libraries
        assert "mysql" in libraries

    def test_get_topic_for_step(self, service):
        """Test topic selection for different steps."""
        assert "project structure" in service._get_topic_for_step("3-system-template")
        assert "design patterns" in service._get_topic_for_step("4-systems-patterns")
        assert "testing" in service._get_topic_for_step("7-tests")
        assert "api reference" in service._get_topic_for_step("unknown-step")

    def test_get_step_specific_libraries(self, service):
        """Test step-specific library recommendations."""
        libs = service.get_step_specific_libraries("3-system-template")
        assert "react" in libs
        assert "fastapi" in libs
        
        libs = service.get_step_specific_libraries("7-tests")
        assert "pytest" in libs
        assert "jest" in libs

    def test_cache_validity(self, service):
        """Test cache entry validity checking."""
        # Valid cache entry (recent)
        valid_entry = {
            "timestamp": datetime.now().isoformat(),
            "library_id": "test-lib"
        }
        assert service._is_cache_valid(valid_entry)
        
        # Invalid cache entry (old)
        old_entry = {
            "timestamp": (datetime.now() - timedelta(days=8)).isoformat(),
            "library_id": "test-lib"
        }
        assert not service._is_cache_valid(old_entry)
        
        # Invalid cache entry (no timestamp)
        invalid_entry = {"library_id": "test-lib"}
        assert not service._is_cache_valid(invalid_entry)

    def test_format_library_docs_section(self, service):
        """Test documentation formatting."""
        library_docs = {
            "react": "React documentation content",
            "fastapi": "FastAPI documentation content"
        }
        
        formatted = service.format_library_docs_section(library_docs)
        
        assert "## Context7 Library Documentation" in formatted
        assert "### React Documentation" in formatted
        assert "### Fastapi Documentation" in formatted
        assert "React documentation content" in formatted
        assert "FastAPI documentation content" in formatted

    def test_format_library_docs_empty(self, service):
        """Test empty documentation formatting."""
        formatted = service.format_library_docs_section({})
        assert formatted == ""

    @patch('ai_sdlc.services.context7_service.Context7Client')
    def test_enrich_prompt_with_cache_hit(self, mock_client_class, service, temp_cache_dir):
        """Test prompt enrichment with cached documentation."""
        # Setup cache
        cache_key = "react_3-system-template"
        cache_file = temp_cache_dir / f"{cache_key}.md"
        cache_file.write_text("Cached React docs")
        
        service.cache_index[cache_key] = {
            "timestamp": datetime.now().isoformat(),
            "library_id": "/react/react"
        }
        service._save_cache_index()
        
        # Test enrichment
        prompt = "Build a system with <context7_docs></context7_docs>"
        previous_content = "Using React for frontend"
        
        enriched = service.enrich_prompt(prompt, "3-system-template", previous_content)
        
        assert "Cached React docs" in enriched
        assert "<context7_docs>" not in enriched
        mock_client_class.return_value.resolve_library_id.assert_not_called()

    @patch('ai_sdlc.services.context7_service.Context7Client')
    def test_enrich_prompt_with_cache_miss(self, mock_client_class, service):
        """Test prompt enrichment without cache."""
        # Setup mock client
        mock_client = Mock()
        mock_client.resolve_library_id.return_value = "/vue/vue"
        mock_client.get_library_docs.return_value = "Fresh Vue docs"
        mock_client_class.return_value = mock_client
        
        # Test enrichment
        prompt = "Build a system"
        previous_content = "Using Vue for frontend"
        
        enriched = service.enrich_prompt(prompt, "3-system-template", previous_content)
        
        assert "Fresh Vue docs" in enriched
        mock_client.resolve_library_id.assert_called_once_with("vue")
        mock_client.get_library_docs.assert_called_once()

    def test_create_context_command_output(self, service):
        """Test context command output formatting."""
        detected_libs = ["react", "fastapi", "postgresql"]
        output = service.create_context_command_output("3-system-template", detected_libs)
        
        assert "Context7 Library Detection" in output
        assert "react" in output
        assert "fastapi" in output
        assert "postgresql" in output
        assert "These libraries will be included" in output

    def test_create_context_command_output_no_libs(self, service):
        """Test context command output with no libraries."""
        output = service.create_context_command_output("3-system-template", [])
        
        assert "No libraries detected" in output
        assert "aisdlc context --libraries" in output

    def test_cache_locking(self, service, temp_cache_dir):
        """Test cache file locking mechanism."""
        # Test acquire and release lock
        service._acquire_lock()
        assert service.cache_lock_file.exists()
        
        service._release_lock()
        # Lock file still exists but is unlocked
        assert service.cache_lock_file.exists()

    def test_library_patterns_compiled(self):
        """Test that library patterns are pre-compiled."""
        from ai_sdlc.services.context7_service import LIBRARY_PATTERNS
        
        assert len(LIBRARY_PATTERNS) > 0
        for pattern in LIBRARY_PATTERNS:
            # Verify these are compiled regex objects
            assert hasattr(pattern, 'pattern')
            assert hasattr(pattern, 'findall')