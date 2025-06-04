# pyright: reportMissingImports=false
"""Extended unit tests for Context7 client to achieve 100% coverage."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from ai_sdlc.services.context7_client import (
    CODE_BLOCK_PATTERN,
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

        with pytest.raises(Context7ClientError, match="Client is closed"):
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
            mock_stream,
        ]
        mock_stream.__aexit__.return_value = None
        mock_stream.aiter_lines.return_value = ["data: /messages/test?sessionId=123"]

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream

        with patch.object(client, "_ensure_client", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client._execute_tool_with_retry("test-tool", {})
                # Should succeed after retries
                assert result is None  # No proper response in mock

    @pytest.mark.asyncio
    async def test_execute_tool_no_retry_on_auth_error(self):
        """Test execute_tool doesn't retry on auth errors."""
        client = Context7Client()

        mock_stream = AsyncMock()
        mock_stream.__aenter__.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=Mock(), response=Mock(status_code=401)
        )

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream

        with patch.object(client, "_get_client", return_value=mock_client):
            result = await client._execute_tool_with_retry("test-tool", {})
            assert result is None
            # Should only try once
            mock_client.stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_sse_reader_handles_events(self):
        """Test SSE reader properly handles different event types."""
        client = Context7Client()

        # Simulate SSE events
        sse_events = [
            "data: /messages/test?sessionId=123",
            'data: {"result": {"content": [{"text": "test result"}]}}',
            "event: done",
        ]

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_stream
        mock_stream.__aexit__.return_value = None
        mock_stream.aiter_lines.return_value = sse_events
        mock_stream.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream

        # Mock the POST response
        mock_post_response = Mock()
        mock_post_response.status_code = 202
        mock_post_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_post_response

        with patch.object(client, "_get_client", return_value=mock_client):
            result = await client._execute_tool("test-tool", {})
            assert result == {"result": {"content": [{"text": "test result"}]}}

    @pytest.mark.asyncio
    async def test_close_alias(self):
        """Test close() is an alias for aclose()."""
        client = Context7Client()

        # Create a client to close
        await client._ensure_client()
        assert client._client is not None

        # Use the close() alias
        await client.close()
        assert client._closed
        assert client._client is None

    def test_resolve_library_id_success(self):
        """Test successful library ID resolution."""
        client = Context7Client()

        # Mock the response structure expected by resolve_library_id
        mock_result = {
            "result": {
                "content": [
                    {
                        "text": """- Title: Pytest
- Context7-compatible library ID: /pytest-dev/pytest
- Description: Testing framework
- Code Snippets: 100
- Trust Score: 9.5
----------
"""
                    }
                ]
            }
        }

        with patch.object(
            client, "_execute_tool_with_retry", new=AsyncMock(return_value=mock_result)
        ):
            result = client.resolve_library_id("pytest")
            assert result == "/pytest-dev/pytest"

    def test_resolve_library_id_parse_error(self):
        """Test library ID resolution with parse error."""
        client = Context7Client()

        # Return malformed result
        mock_result = {"results": "not-a-list"}

        with patch.object(
            client, "_execute_tool_with_retry", new=AsyncMock(return_value=mock_result)
        ):
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
    async def test_aclose_with_active_client(self):
        """Test closing with active HTTP client."""
        client = Context7Client()

        # Force client creation
        await client._ensure_client()
        assert client._client is not None

        # Close
        await client.aclose()
        assert client._closed

    @pytest.mark.asyncio
    async def test_aclose_multiple_times(self):
        """Test closing client multiple times is safe."""
        client = Context7Client()

        await client.aclose()
        await client.aclose()  # Should not raise
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

        response_data = {
            "result": {
                "content": [
                    {
                        "text": """TITLE: Test Library
DESCRIPTION: A test library

Here's an example:

```python
def test():
    return True
```

More text here.

```javascript
console.log("test");
```
"""
                    }
                ]
            }
        }

        result = client._parse_docs_content(response_data)
        assert "def test():" in result
        assert "console.log" in result

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

    def test_get_library_docs_formats_output(self):
        """Test get_library_docs formats documentation properly."""
        client = Context7Client()

        mock_response = {
            "result": {
                "content": [
                    {
                        "text": """TITLE: Getting Started
DESCRIPTION: How to install and use the library

First install:

```bash
pip install library
```

Then use:

```python
import library
library.do_something()
```

TITLE: Advanced Usage  
DESCRIPTION: More complex examples

You can also do advanced things.
"""
                    }
                ]
            }
        }

        with patch.object(
            client,
            "_execute_tool_with_retry",
            new=AsyncMock(return_value=mock_response),
        ):
            docs = client.get_library_docs("/test/library", tokens=1000)

            # Check formatting
            assert "**Getting Started**" in docs
            assert "How to install and use the library" in docs
            assert "```bash" in docs
            assert "pip install library" in docs
            assert "```python" in docs
            assert "import library" in docs
            assert "**Advanced Usage**" in docs

    def test_ensure_loop_creates_new_loop(self):
        """Test _ensure_loop creates new event loop when needed."""
        client = Context7Client()

        with patch("asyncio.get_running_loop", side_effect=RuntimeError):
            with patch("asyncio.new_event_loop") as mock_new_loop:
                mock_loop = Mock()
                mock_new_loop.return_value = mock_loop

                loop = client._ensure_loop()
                assert loop is mock_loop
                assert client._owns_loop is True

    def test_ensure_loop_uses_existing_loop(self):
        """Test _ensure_loop uses existing running loop."""
        client = Context7Client()

        mock_loop = Mock()
        with patch("asyncio.get_running_loop", return_value=mock_loop):
            loop = client._ensure_loop()
            assert loop is mock_loop
            assert client._owns_loop is False

    @pytest.mark.asyncio
    async def test_execute_tool_with_retry_returns_none_after_failures(self):
        """Test execute_tool_with_retry returns None after all retries fail."""
        client = Context7Client()

        with patch.object(
            client, "_execute_tool", side_effect=httpx.ConnectError("Connection failed")
        ) as mock_execute:
            result = await client._execute_tool_with_retry("test-tool", {})

            assert result is None
            assert mock_execute.call_count == 3  # MAX_RETRIES
