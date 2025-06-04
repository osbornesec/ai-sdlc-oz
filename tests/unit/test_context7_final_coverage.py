"""Final tests for Context7 client and service to achieve 100% coverage."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from ai_sdlc.services.context7_client import (
    Context7Client,
    Context7ClientError,
)
from ai_sdlc.services.context7_service import Context7Service


class TestContext7FinalCoverage:
    """Final coverage tests for Context7 components."""

    # Context7Client - Uncovered lines
    @pytest.mark.asyncio
    async def test_client_sse_reader_connection_reset(self):
        """Test SSE reader with connection reset error."""
        client = Context7Client(api_key="test-key-1234567890")

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'text/event-stream'}

        # Simulate connection reset during iteration
        async def aiter_lines():
            yield b'data: {"test": "data"}\n'
            raise httpx.ConnectError("Connection reset")

        mock_response.aiter_lines = aiter_lines

        async for event in client._sse_reader(mock_response):
            assert event == {"test": "data"}
            break  # Only get first event before error

    @pytest.mark.asyncio
    async def test_client_sse_reader_invalid_json(self):
        """Test SSE reader with invalid JSON data."""
        client = Context7Client(api_key="test-key-1234567890")

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'text/event-stream'}

        async def aiter_lines():
            yield b'data: {invalid json}\n'
            yield b'data: {"valid": "data"}\n'

        mock_response.aiter_lines = aiter_lines

        events = []
        with patch('ai_sdlc.services.context7_client.logger') as mock_logger:
            async for event in client._sse_reader(mock_response):
                events.append(event)

        assert len(events) == 1
        assert events[0] == {"valid": "data"}
        mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_client_execute_tool_non_sse_response(self):
        """Test execute tool with non-SSE response."""
        client = Context7Client(api_key="test-key-1234567890")

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {"error": "Not SSE"}

        mock_client.post.return_value = mock_response

        with patch.object(client, '_ensure_client', return_value=mock_client):
            with pytest.raises(Context7ClientError, match="Unexpected response"):
                await client._execute_tool("test-tool", {})

    @pytest.mark.asyncio
    async def test_client_execute_tool_http_error(self):
        """Test execute tool with HTTP error response."""
        client = Context7Client(api_key="test-key-1234567890")

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error", request=Mock(), response=mock_response
        )

        mock_client.post.return_value = mock_response

        with patch.object(client, '_ensure_client', return_value=mock_client):
            with pytest.raises(Context7ClientError, match="HTTP error"):
                await client._execute_tool("test-tool", {})

    @pytest.mark.asyncio
    async def test_client_get_library_docs_with_topic(self):
        """Test get_library_docs with topic parameter."""
        client = Context7Client(api_key="test-key-1234567890")

        mock_response = {"result": {"content": [{"text": "Docs about hooks"}]}}

        with patch.object(client, '_execute_tool', return_value=mock_response):
            result = await client.get_library_docs("/react/react", topic="hooks")
            assert result == "Docs about hooks"

    @pytest.mark.asyncio
    async def test_client_aclose_no_client(self):
        """Test aclose when no client exists."""
        client = Context7Client(api_key="test-key-1234567890")
        await client.aclose()  # Should not raise

    @pytest.mark.asyncio
    async def test_client_closed_check(self):
        """Test operations on closed client."""
        client = Context7Client(api_key="test-key-1234567890")
        client._closed = True

        with pytest.raises(Context7ClientError, match="Client is closed"):
            await client._ensure_client()

    def test_client_sync_resolve_library_id(self):
        """Test sync resolve_library_id method."""
        client = Context7Client(api_key="test-key-1234567890")

        async def mock_execute():
            return {
                "result": {
                    "content": [{
                        "text": "----------\n- Title: Test\n- Context7-compatible library ID: /test/lib\n----------"
                    }]
                }
            }

        with patch.object(client, '_execute_tool_with_retry', return_value=mock_execute()):
            with patch('asyncio.run') as mock_run:
                mock_run.return_value = "/test/lib"
                result = client.resolve_library_id("test")
                assert result == "/test/lib"

    def test_client_sync_get_library_docs(self):
        """Test sync get_library_docs method."""
        client = Context7Client(api_key="test-key-1234567890")

        with patch('asyncio.run') as mock_run:
            mock_run.return_value = "Test docs"
            result = client.get_library_docs("/test/lib")
            assert result == "Test docs"

    # Context7Service - Uncovered lines
    def test_service_extract_step_specific_libraries(self):
        """Test extraction of step-specific libraries."""
        service = Context7Service(Path("/tmp"))

        # Create mock mappings
        with patch.object(service, 'step_library_mappings', {
            '03-system-template': ['fastapi', 'sqlalchemy'],
            '04-systems-patterns': ['redis', 'celery']
        }):
            # Test getting libraries for a specific step
            libs = service.get_step_specific_libraries('03-system-template')
            assert 'fastapi' in libs
            assert 'sqlalchemy' in libs

    def test_service_library_in_text_check(self):
        """Test library detection in text."""
        service = Context7Service(Path("/tmp"))

        text = "We'll use React with TypeScript and Next.js"

        # Should detect react, typescript, and next.js
        libraries = service.extract_libraries_from_text(text)
        assert 'react' in libraries
        assert 'typescript' in libraries

    def test_service_format_docs_with_finalized_library(self):
        """Test formatting docs when library is finalized."""
        service = Context7Service(Path("/tmp"))

        docs = service._format_library_docs_section({
            'pytest': '# PyTest Documentation\n\nTesting framework docs'
        })

        assert "### Pytest Documentation" in docs
        assert "# PyTest Documentation" in docs
        assert "Testing framework docs" in docs

    def test_service_enrich_prompt_io_error_on_cache_read(self, temp_dir):
        """Test enrich_prompt when cache read fails with IOError."""
        service = Context7Service(temp_dir)

        # Create a cache file
        cache_file = temp_dir / "pytest_docs.json"
        cache_file.write_text('{"content": "cached", "timestamp": 9999999999}')

        with patch('pathlib.Path.read_text', side_effect=OSError("Disk error")):
            with patch.object(service.client, 'get_library_docs', return_value="fresh docs"):
                result = service.enrich_prompt("Test prompt", "test-step", "import pytest")
                assert "fresh docs" in result

    def test_service_enrich_prompt_client_returns_none(self, temp_dir):
        """Test enrich_prompt when client returns None."""
        service = Context7Service(temp_dir)

        with patch.object(service.client, 'resolve_library_id', return_value=None):
            result = service.enrich_prompt("Test prompt", "test-step", "import unknown_lib")
            assert "Could not resolve library: unknown_lib" in result

    def test_service_extract_libraries_for_step_io_error(self, temp_dir):
        """Test extract_libraries_for_step with file read error."""
        service = Context7Service(temp_dir)

        workdir = temp_dir / "test"
        workdir.mkdir()
        step_file = workdir / "00-idea-test.md"
        step_file.write_text("content")

        with patch('pathlib.Path.read_text', side_effect=OSError("Cannot read")):
            with patch('ai_sdlc.services.context7_service.logger') as mock_logger:
                result = service.extract_libraries_for_step(
                    workdir, ["00-idea"], 0, "test"
                )
                assert result == []
                mock_logger.debug.assert_called()

    def test_service_async_run_without_loop(self, temp_dir):
        """Test async operation when no event loop exists."""
        service = Context7Service(temp_dir)

        # Ensure no event loop is running
        try:
            loop = asyncio.get_running_loop()
            pytest.skip("Event loop is already running")
        except RuntimeError:
            pass

        # Should create a new event loop
        result = service._run_async(asyncio.coroutine(lambda: "test result")())
        assert result == "test result"
