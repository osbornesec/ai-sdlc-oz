
# pyright: reportMissingImports=false
"""Unit tests for Context7 client."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from ai_sdlc.services.context7_client import (
    Context7Client, 
    Context7ClientError,
    Context7AuthError,
    Context7TimeoutError,
    CODE_BLOCK_PATTERN
)


class TestContext7Client:
    """Test Context7Client functionality."""

    @pytest.fixture
    def client(self):
        """Create a Context7Client instance."""
        with patch.dict('os.environ', {'CONTEXT7_API_KEY': 'test-key'}):
            return Context7Client()

    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        client = Context7Client(api_key="direct-key")
        assert client.api_key == "direct-key"
        assert client.base_url == "https://mcp.context7.com"

    def test_init_with_env_key(self):
        """Test client initialization with environment key."""
        with patch.dict('os.environ', {'CONTEXT7_API_KEY': 'env-key'}):
            client = Context7Client()
            assert client.api_key == "env-key"

    def test_init_without_key(self):
        """Test client initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('ai_sdlc.services.context7_client.logger') as mock_logger:
                client = Context7Client()
                assert client.api_key is None
                mock_logger.warning.assert_called_once()

    def test_api_key_validation(self):
        """Test API key validation logic."""
        client = Context7Client()
        
        # Valid keys
        assert client._is_valid_api_key("valid-test-key-123")
        assert client._is_valid_api_key("abcdefghijklmnop")
        assert client._is_valid_api_key("test_key_with_underscores")
        assert client._is_valid_api_key("test.key.with.dots")
        
        # Invalid keys
        assert not client._is_valid_api_key("")
        assert not client._is_valid_api_key("short")
        assert not client._is_valid_api_key("has spaces")
        assert not client._is_valid_api_key("has@special")

    def test_init_with_invalid_api_key(self):
        """Test client initialization with invalid API key."""
        with patch('ai_sdlc.services.context7_client.logger') as mock_logger:
            client = Context7Client(api_key="bad")
            assert client.api_key is None  # Should be set to None due to validation
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        client = Context7Client(api_key="test-key-123456789")
        
        async with client as ctx_client:
            assert ctx_client is client
            assert not client._closed
            assert client._client is not None
        
        assert client._closed

    @pytest.mark.asyncio
    async def test_loop_closed_after_context_exit(self):
        """Event loop created by client should be closed on exit."""
        loop = asyncio.new_event_loop()
        with patch("asyncio.get_running_loop", side_effect=RuntimeError()):
            with patch("asyncio.new_event_loop", return_value=loop):
                async with Context7Client(api_key="test-key-123456789") as client:
                    # Force loop creation
                    client._ensure_loop()

        assert loop.is_closed()

    def test_closed_client_raises_error(self):
        """Test that using closed client raises error."""
        client = Context7Client(api_key="test-key-123456789")
        client._closed = True
        
        with pytest.raises(Context7ClientError, match="Client is closed"):
            client.resolve_library_id("test")

    def test_connection_pooling_config(self, client):
        """Test connection pooling configuration."""
        assert client.limits.max_keepalive_connections == 5
        assert client.limits.max_connections == 10
        assert client.limits.keepalive_expiry == 30.0

    def test_parse_library_results(self, client):
        """Test parsing library results from text."""
        text = """
        ----------
        - Title: React
        - Context7-compatible library ID: /facebook/react
        - Description: A JavaScript library for building user interfaces
        - Code Snippets: 150
        - Trust Score: 9.5
        ----------
        - Title: Vue
        - Context7-compatible library ID: /vuejs/vue
        - Description: Progressive JavaScript Framework
        - Code Snippets: 120
        - Trust Score: 9.0
        ----------
        """
        
        results = client._parse_library_results(text)
        
        assert len(results) == 2
        assert results[0]["name"] == "React"
        assert results[0]["libraryId"] == "/facebook/react"
        assert results[0]["codeSnippetCount"] == 150
        assert results[0]["trustScore"] == 9.5
        
        assert results[1]["name"] == "Vue"
        assert results[1]["libraryId"] == "/vuejs/vue"

    def test_parse_library_results_invalid_data(self, client):
        """Test parsing with invalid data."""
        text = """
        ----------
        - Title: Invalid
        - Code Snippets: not-a-number
        - Trust Score: invalid
        ----------
        """
        
        with patch('ai_sdlc.services.context7_client.logger') as mock_logger:
            results = client._parse_library_results(text)
            
            # Should still parse what it can
            assert len(results) == 0  # No library ID, so not included
            # Should log debug messages for invalid values
            assert mock_logger.debug.call_count >= 2

    def test_parse_docs_content(self, client):
        """Test parsing documentation content."""
        response_data = {
            "result": {
                "content": [
                    {"text": "First part of docs"},
                    {"text": "Second part of docs"},
                    {"other": "ignored"}
                ]
            }
        }
        
        content = client._parse_docs_content(response_data)
        assert content == "First part of docs\nSecond part of docs"

    def test_parse_docs_content_empty(self, client):
        """Test parsing empty documentation."""
        assert client._parse_docs_content({}) == ""
        assert client._parse_docs_content({"result": {}}) == ""
        assert client._parse_docs_content({"result": {"content": []}}) == ""

    @pytest.mark.asyncio
    async def test_retry_logic_on_timeout(self):
        """Test retry logic handles timeouts correctly."""
        client = Context7Client(api_key="test-key-123456789")
        
        with patch.object(client, '_execute_tool', side_effect=Context7TimeoutError("Timeout")) as mock_execute:
            result = await client._execute_tool_with_retry("test-tool", {})
            
            # Should have tried 3 times (MAX_RETRIES)
            assert mock_execute.call_count == 3
            assert result is None

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self):
        """Test that auth errors are not retried."""
        client = Context7Client(api_key="test-key-123456789")
        
        with patch.object(client, '_execute_tool', side_effect=Context7AuthError("Auth failed")) as mock_execute:
            result = await client._execute_tool_with_retry("test-tool", {})
            
            # Should only try once for auth errors
            assert mock_execute.call_count == 1
            assert result is None

    def test_resolve_library_id_with_mocked_retry(self, client):
        """Test resolving library ID with retry logic."""
        mock_response = {
            "result": {
                "content": [{
                    "text": """
                    ----------
                    - Title: React
                    - Context7-compatible library ID: /facebook/react
                    - Trust Score: 9.5
                    ----------
                    """
                }]
            }
        }
        
        # Mock the retry method to return our response
        with patch.object(
            client,
            '_execute_tool_with_retry',
            new=AsyncMock(return_value=mock_response),
        ) as mock_retry:
            result = client.resolve_library_id("react")
        
        assert result == "/facebook/react"
        mock_retry.assert_called_once_with("resolve-library-id", {"libraryName": "react"})

    @patch('asyncio.new_event_loop')
    def test_resolve_library_id_error_handling(self, mock_new_loop, client):
        """Test error handling in resolve_library_id."""
        mock_loop = Mock()
        mock_new_loop.return_value = mock_loop

        def run_until_complete_side_effect(coro):
            asyncio.run(coro)
            raise asyncio.TimeoutError()

        mock_loop.run_until_complete.side_effect = run_until_complete_side_effect

        with patch('ai_sdlc.services.context7_client.logger') as mock_logger, patch.object(
            client,
            '_execute_tool_with_retry',
            new=AsyncMock(return_value=None),
        ):
            result = client.resolve_library_id("test")
        
        assert result is None
        mock_logger.error.assert_called_once()
        mock_loop.close.assert_called_once()

    def test_get_client_creates_new(self, client):
        """Test that _get_client creates new client when needed."""
        assert client._client is None
        
        http_client = client._get_client()
        assert http_client is not None
        assert isinstance(http_client, httpx.AsyncClient)
        assert client._client is http_client

    def test_get_client_reuses_existing(self, client):
        """Test that _get_client reuses existing client."""
        http_client1 = client._get_client()
        http_client2 = client._get_client()
        assert http_client1 is http_client2

    def test_code_block_pattern(self):
        """Test the pre-compiled code block pattern."""
        text = """
        Some text
        ```python
        def hello():
            print("world")
        ```
        More text
        ```javascript
        console.log("test");
        ```
        """
        
        parts = CODE_BLOCK_PATTERN.split(text)
        assert len(parts) == 7  # text, lang, code, text, lang, code, text
        assert parts[1] == "python"
        assert "def hello():" in parts[2]
        assert parts[4] == "javascript"
        assert "console.log" in parts[5]

    @pytest.mark.asyncio
    async def test_execute_tool_timeout(self, client):
        """Test timeout handling in _execute_tool."""
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            # Mock stream to timeout
            async def iter_lines():
                raise asyncio.TimeoutError()
                yield  # pragma: no cover

            mock_stream = Mock()
            mock_stream.aiter_lines = iter_lines
            mock_stream.raise_for_status = Mock()
            cm = AsyncMock()
            cm.__aenter__.return_value = mock_stream
            cm.__aexit__.return_value = None
            mock_client.stream.return_value = cm

            result = await client._execute_tool("test-tool", {})
            assert result is None