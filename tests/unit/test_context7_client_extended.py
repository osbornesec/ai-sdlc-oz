"""Extended unit tests for Context7 client to achieve 100% coverage."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from ai_sdlc.services.context7_client import (
    CODE_BLOCK_PATTERN,
    Context7AuthError,
    Context7Client,
    Context7ClientError,
    Context7TimeoutError,
)


class TestContext7ClientExtended:
    """Extended test cases for Context7Client."""

    @pytest.mark.asyncio
    async def test_ensure_client_creates_new(self):
        """Test _ensure_client creates new client when needed."""
        client = Context7Client()
        assert client._client is None
        
        async_client = await client._ensure_client()
        assert async_client is not None
        assert isinstance(async_client, httpx.AsyncClient)
        assert client._client is async_client
        
        await client.close()

    @pytest.mark.asyncio
    async def test_ensure_client_reuses_existing(self):
        """Test _ensure_client reuses existing client."""
        client = Context7Client()
        
        # Create first client
        async_client1 = await client._ensure_client()
        # Get again - should be same instance
        async_client2 = await client._ensure_client()
        
        assert async_client1 is async_client2
        
        await client.close()

    @pytest.mark.asyncio
    async def test_ensure_client_when_closed(self):
        """Test _ensure_client raises error when client is closed."""
        client = Context7Client()
        client._closed = True
        
        with pytest.raises(Context7ClientError, match="Client has been closed"):
            await client._ensure_client()

    @pytest.mark.asyncio
    async def test_execute_tool_retry_on_timeout(self):
        """Test execute_tool retries on timeout."""
        client = Context7Client()
        
        mock_response = AsyncMock()
        mock_response.text = "Test response"
        
        # First two calls timeout, third succeeds
        mock_stream = AsyncMock()
        mock_stream.__aenter__.side_effect = [
            httpx.TimeoutException("timeout"),
            httpx.TimeoutException("timeout"),
            mock_stream
        ]
        mock_stream.__aexit__.return_value = None
        mock_stream.aiter_text.return_value = ["data: test\n\n"]
        
        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream
        
        with patch.object(client, '_ensure_client', return_value=mock_client):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await client._execute_tool("test-tool", {})
                # Should succeed after retries
                assert result is not None

    @pytest.mark.asyncio
    async def test_execute_tool_no_retry_on_auth_error(self):
        """Test execute_tool doesn't retry on auth errors."""
        client = Context7Client()
        
        mock_stream = AsyncMock()
        mock_stream.__aenter__.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=Mock(),
            response=Mock(status_code=401)
        )
        
        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream
        
        with patch.object(client, '_ensure_client', return_value=mock_client):
            result = await client._execute_tool("test-tool", {})
            assert result is None
            # Should only try once
            mock_client.stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_sse_reader_handles_events(self):
        """Test SSE reader properly handles different event types."""
        client = Context7Client()
        
        # Simulate SSE events
        sse_events = [
            'event: endpoint\ndata: {"url": "http://test-endpoint"}\n\n',
            'event: session\ndata: {"id": "test-session"}\n\n',
            'event: result\ndata: {"content": "test result"}\n\n',
            'event: error\ndata: {"message": "test error"}\n\n',
            'event: done\ndata: {}\n\n',
        ]
        
        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_stream
        mock_stream.__aexit__.return_value = None
        mock_stream.aiter_text.return_value = sse_events
        
        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream
        
        with patch.object(client, '_ensure_client', return_value=mock_client):
            result = await client._execute_tool("test-tool", {})
            assert result == {"content": "test result"}

    @pytest.mark.asyncio
    async def test_get_library_docs_success(self):
        """Test successful library documentation fetch."""
        client = Context7Client()
        
        mock_result = {"content": "# Library Docs\n\nTest documentation"}
        
        with patch.object(client, '_execute_tool', new_callable=AsyncMock, return_value=mock_result):
            docs = await client.get_library_docs("/test/library", "test topic", 1000)
            assert "# Library Docs" in docs
            assert "Test documentation" in docs

    @pytest.mark.asyncio
    async def test_get_library_docs_no_content(self):
        """Test library docs when no content returned."""
        client = Context7Client()
        
        with patch.object(client, '_execute_tool', new_callable=AsyncMock, return_value=None):
            docs = await client.get_library_docs("/test/library", "test", 1000)
            assert docs == ""

    @pytest.mark.asyncio
    async def test_get_library_docs_empty_content(self):
        """Test library docs with empty content."""
        client = Context7Client()
        
        with patch.object(client, '_execute_tool', new_callable=AsyncMock, return_value={"content": ""}):
            docs = await client.get_library_docs("/test/library", "test", 1000)
            assert docs == ""

    def test_resolve_library_id_success(self):
        """Test successful library ID resolution."""
        client = Context7Client()
        
        # Mock the response structure expected by resolve_library_id
        mock_result = {
            "result": {
                "content": [{
                    "text": """- Title: Pytest
                    - Context7-compatible library ID: /pytest-dev/pytest
                    - Description: Testing framework
                    - Code Snippets: 100
                    - Trust Score: 9.5
                    ----------
                    """
                }]
            }
        }
        
        with patch.object(client, '_execute_tool_with_retry', new=AsyncMock(return_value=mock_result)):
            result = client.resolve_library_id("pytest")
            assert result == "/pytest-dev/pytest"

    def test_resolve_library_id_parse_error(self):
        """Test library ID resolution with parse error."""
        client = Context7Client()
        
        # Return malformed result
        mock_result = {"results": "not-a-list"}
        
        with patch.object(client, '_execute_tool_with_retry', new=AsyncMock(return_value=mock_result)):
            result = client.resolve_library_id("pytest")
            assert result is None

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        async with Context7Client() as client:
            assert not client._closed
            assert client._client is None  # Not created until needed
        
        # After exiting, client should be closed
        assert client._closed

    @pytest.mark.asyncio
    async def test_close_with_active_client(self):
        """Test closing with active HTTP client."""
        client = Context7Client()
        
        # Force client creation
        await client._ensure_client()
        assert client._client is not None
        
        # Close
        await client.close()
        assert client._closed
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_multiple_times(self):
        """Test closing client multiple times is safe."""
        client = Context7Client()
        
        await client.close()
        await client.close()  # Should not raise
        assert client._closed

    def test_is_valid_api_key(self):
        """Test API key validation."""
        client = Context7Client()
        
        # Valid keys
        assert client._is_valid_api_key("sk-proj-abcd1234")
        assert client._is_valid_api_key("sk-test-1234567890")
        assert client._is_valid_api_key("custom-key-format-123")
        
        # Invalid keys
        assert not client._is_valid_api_key("")
        assert not client._is_valid_api_key("   ")
        assert not client._is_valid_api_key("short")
        assert not client._is_valid_api_key(None)

    def test_parse_docs_content_with_code_blocks(self):
        """Test parsing docs content preserves code blocks."""
        client = Context7Client()
        
        content = '''
# Test Library

Here's an example:

```python
def test():
    return True
```

More text here.

```javascript
console.log("test");
```
'''
        
        result = client._parse_docs_content(content)
        assert "```python" in result
        assert "def test():" in result
        assert "```javascript" in result
        assert "console.log" in result

    @pytest.mark.asyncio
    async def test_execute_tool_connection_error_exhausts_retries(self):
        """Test execute_tool exhausts retries on connection errors."""
        client = Context7Client()
        
        mock_stream = AsyncMock()
        mock_stream.__aenter__.side_effect = httpx.ConnectError("Connection failed")
        
        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream
        
        with patch.object(client, '_ensure_client', return_value=mock_client):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(httpx.ConnectError):
                    await client._execute_tool("test-tool", {})
                
                # Should retry MAX_RETRIES times
                assert mock_client.stream.call_count == 3  # MAX_RETRIES = 3

    @pytest.mark.asyncio
    async def test_execute_tool_sse_timeout(self):
        """Test SSE reader handles timeout waiting for endpoint."""
        client = Context7Client()
        
        # Simulate SSE that never sends endpoint
        async def slow_iter():
            await asyncio.sleep(0.1)
            yield 'event: other\ndata: {}\n\n'
        
        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_stream
        mock_stream.__aexit__.return_value = None
        mock_stream.aiter_text = slow_iter
        
        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream
        
        client.timeout = httpx.Timeout(0.05)  # Very short timeout
        
        with patch.object(client, '_ensure_client', return_value=mock_client):
            with pytest.raises(Context7TimeoutError, match="Timeout waiting for SSE endpoint"):
                await client._execute_tool("test-tool", {})

    def test_code_block_pattern_matching(self):
        """Test the CODE_BLOCK_PATTERN regex."""
        # Test basic match
        match = CODE_BLOCK_PATTERN.search("```python\ncode\n```")
        assert match is not None
        assert match.group(1) == "python"
        assert match.group(2) == "code\n"
        
        # Test with no language
        match = CODE_BLOCK_PATTERN.search("```\ncode\n```")
        assert match is not None
        assert match.group(1) == ""
        assert match.group(2) == "code\n"
        
        # Test multiline code
        match = CODE_BLOCK_PATTERN.search("```js\nline1\nline2\nline3\n```")
        assert match is not None
        assert match.group(1) == "js"
        assert "line1\nline2\nline3\n" in match.group(2)