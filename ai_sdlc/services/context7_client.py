"""Context7 client for fetching library documentation via SSE API."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

# Pre-compiled regex for parsing documentation code blocks
CODE_BLOCK_PATTERN = re.compile(r'```(\w*)\n(.*?)```', re.DOTALL)

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0
RETRY_STATUS_CODES = {502, 503, 504, 429}


class Context7ClientError(Exception):
    """Base exception for Context7 client errors."""
    pass


class Context7TimeoutError(Context7ClientError):
    """Timeout error for Context7 operations."""
    pass


class Context7Client:
    """Context7 client that properly handles SSE connections with async context manager support."""

    def __init__(self, base_url: str = "https://mcp.context7.com"):
        """Initialize Context7 client.

        Args:
            base_url: The base URL for Context7 API
        """
        self.base_url = base_url
        self.timeout = httpx.Timeout(60.0, connect=10.0)

        # Configure connection pooling
        self.limits = httpx.Limits(
            max_keepalive_connections=5,
            max_connections=10,
            keepalive_expiry=30.0
        )

        # Shared async client and event loop management
        self._client: httpx.AsyncClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._own_loop: bool = False
        self._closed = False

    async def __aenter__(self) -> Context7Client:
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any | None) -> None:
        """Async context manager exit with proper cleanup."""
        await self.aclose()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure async client is available and create if needed."""
        if self._closed:
            raise Context7ClientError("Client is closed")

        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=self.limits
            )
        return self._client

    def _get_client(self) -> httpx.AsyncClient:
        """Synchronously get or create the underlying HTTP client."""
        loop = self._ensure_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._ensure_client(), loop
            )
            return future.result()
        return loop.run_until_complete(self._ensure_client())

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        """Ensure event loop is available for sync methods."""
        if self._loop is None or self._loop.is_closed():
            try:
                # Try to get existing loop
                self._loop = asyncio.get_running_loop()
                self._own_loop = False
            except RuntimeError:
                # No running loop, create new one
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._own_loop = True
        return self._loop

    async def aclose(self) -> None:
        """Properly close the async client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        if self._own_loop and self._loop and not self._loop.is_closed():
            self._loop.close()
        self._closed = True

    async def _execute_tool_with_retry(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any] | None:
        """Execute a tool with retry logic."""
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                return await self._execute_tool(tool_name, parameters)
            except (httpx.ConnectError, httpx.TimeoutException, Context7TimeoutError) as e:
                last_exception = e
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF_FACTOR ** attempt
                    logger.debug(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {MAX_RETRIES} attempts failed for {tool_name}")
            except httpx.HTTPStatusError as e:
                # Don't retry on 4xx errors
                logger.error(f"Non-retryable error for {tool_name}: {e}")
                break

        if last_exception:
            raise last_exception
        return None

    async def _execute_tool(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any] | None:
        """Execute a Context7 tool via SSE API with proper session handling.

        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool

        Returns:
            Response data from the API or None if failed

        Raises:
            Context7TimeoutError: If request times out
            httpx.HTTPError: For HTTP-related errors
        """
        params = {"tool": tool_name}
        params.update(parameters)
        sse_url = f"{self.base_url}/sse?{urlencode(params)}"

        # Use the shared client with connection pooling
        client = self._get_client()

        endpoint = None
        session_id = None
        result_queue: asyncio.Queue[Any] = asyncio.Queue()

        async def sse_reader() -> None:
            """Keep SSE connection alive and read data."""
            headers: dict[str, str] = {}

            try:
                async with client.stream("GET", sse_url, headers=headers) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        await result_queue.put(line)

                        if line.startswith("data: /messages"):
                            endpoint_data = line[6:]
                            await result_queue.put(("endpoint", endpoint_data))
            except httpx.HTTPStatusError as e:
                raise

        # Start SSE reader
        sse_task = asyncio.create_task(sse_reader())

        try:
            # Wait for endpoint
            while True:
                try:
                    item = await asyncio.wait_for(result_queue.get(), timeout=5.0)
                except TimeoutError as e:
                    raise Context7TimeoutError("Timeout waiting for SSE endpoint") from e

                if isinstance(item, tuple) and item[0] == "endpoint":
                    endpoint = item[1]
                    if "sessionId=" in endpoint:
                        session_id = endpoint.split("sessionId=")[1]
                    break

            # Make POST request while SSE is alive
            messages_url = f"{self.base_url}{endpoint}"
            request_data = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                },
                "id": 1
            }

            headers = {
                "Content-Type": "application/json",
                "MCP-Session-Id": session_id
            }

            try:
                post_response = await client.post(
                    messages_url,
                    json=request_data,
                    headers=headers
                )

                if post_response.status_code in RETRY_STATUS_CODES:
                    # Let retry logic handle these
                    post_response.raise_for_status()

                post_response.raise_for_status()

            except httpx.ConnectError as e:
                raise httpx.ConnectError(f"Failed to connect to Context7: {e}") from e
            except httpx.TimeoutException as e:
                raise Context7TimeoutError(f"Context7 request timed out: {e}") from e

            if post_response.status_code == 202:
                # Collect response data
                while True:
                    try:
                        line = await asyncio.wait_for(result_queue.get(), timeout=10.0)

                        if isinstance(line, str) and line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str and data_str != "[DONE]":
                                try:
                                    data = json.loads(data_str)
                                    return data
                                except json.JSONDecodeError as e:
                                    logger.debug(f"Failed to parse JSON response: {e}")
                        elif "event: done" in str(line):
                            break

                    except TimeoutError as e:
                        raise Context7TimeoutError("Timeout waiting for response data") from e

            return None

        finally:
            if sse_task and not sse_task.done():
                sse_task.cancel()
                try:
                    await sse_task
                except asyncio.CancelledError:
                    pass

    def _parse_library_results(self, text: str) -> list[dict[str, Any]]:
        """Parse library results from Context7 text format."""
        results = []

        # Split by separator lines
        entries = text.split("----------")

        for entry in entries:
            if "Context7-compatible library ID:" in entry:
                result: dict[str, Any] = {}
                lines = entry.strip().split("\n")

                for line in lines:
                    line = line.strip("- ").strip()

                    if line.startswith("Title:"):
                        result["name"] = line.replace("Title:", "").strip()
                    elif line.startswith("Context7-compatible library ID:"):
                        result["libraryId"] = line.replace("Context7-compatible library ID:", "").strip()
                    elif line.startswith("Description:"):
                        result["description"] = line.replace("Description:", "").strip()
                    elif line.startswith("Code Snippets:"):
                        try:
                            result["codeSnippetCount"] = int(line.replace("Code Snippets:", "").strip())
                        except ValueError:
                            logger.debug(f"Invalid code snippet count: {line}")
                    elif line.startswith("Trust Score:"):
                        try:
                            result["trustScore"] = float(line.replace("Trust Score:", "").strip())
                        except ValueError:
                            logger.debug(f"Invalid trust score: {line}")

                if "libraryId" in result:
                    results.append(result)

        return results

    def _parse_docs_content(self, response_data: dict[str, Any]) -> str:
        """Parse documentation content from Context7 response."""
        if "result" in response_data:
            result = response_data["result"]

            if isinstance(result, dict) and "content" in result:
                content = result["content"]

                if isinstance(content, list):
                    docs_parts = []

                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            docs_parts.append(item["text"])

                    return "\n".join(docs_parts)

        return ""

    def resolve_library_id(self, library_name: str) -> str | None:
        """Resolve a library name to Context7 library ID.

        Args:
            library_name: Name of the library to resolve

        Returns:
            Context7-compatible library ID or None if not found

        Raises:
            Context7ClientError: If client is closed or other errors occur
        """
        if self._closed:
            raise Context7ClientError("Client is closed")

        try:
            loop = self._ensure_loop()

            response_data = loop.run_until_complete(
                self._execute_tool_with_retry("resolve-library-id", {"libraryName": library_name})
            )

            if response_data and "result" in response_data:
                result = response_data["result"]

                if isinstance(result, dict) and "content" in result:
                    content = result["content"]

                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                # Parse the text to find libraries
                                libraries = self._parse_library_results(item["text"])

                                if libraries:
                                    # Find best match
                                    best_match = None
                                    best_score = -1

                                    for lib in libraries:
                                        # Score based on name match and trust score
                                        score = 0

                                        # Exact name match
                                        if lib.get("name", "").lower() == library_name.lower():
                                            score += 100
                                        # Partial match
                                        elif library_name.lower() in lib.get("name", "").lower():
                                            score += 50

                                        # Add trust score
                                        score += lib.get("trustScore", 0) * 10

                                        # Add snippet count bonus
                                        score += min(lib.get("codeSnippetCount", 0) / 100, 10.0)

                                        if score > best_score:
                                            best_score = score
                                            best_match = lib

                                    if best_match:
                                        return best_match["libraryId"]

            return None

        except Context7TimeoutError:
            logger.error(f"Context7 timeout resolving library ID for: {library_name}")
            return None
        except Exception as e:
            logger.error(f"Error resolving library ID for {library_name}: {e}", exc_info=True)
            return None

    def get_library_docs(
        self,
        library_id: str,
        tokens: int = 5000,
        topic: str | None = None
    ) -> str:
        """Get documentation for a library.

        Args:
            library_id: Context7-compatible library ID
            tokens: Maximum number of tokens to fetch
            topic: Optional topic to focus on

        Returns:
            Formatted documentation string or empty string if failed

        Raises:
            Context7ClientError: If client is closed or other errors occur
        """
        if self._closed:
            raise Context7ClientError("Client is closed")

        try:
            loop = self._ensure_loop()

            args: dict[str, Any] = {
                "context7CompatibleLibraryID": library_id,
                "tokens": tokens
            }
            if topic:
                args["topic"] = topic

            response_data = loop.run_until_complete(
                self._execute_tool_with_retry("get-library-docs", args)
            )

            if response_data:
                docs = self._parse_docs_content(response_data)

                if docs:
                    # Format documentation
                    formatted_docs = []

                    # Split by code blocks using pre-compiled regex
                    parts = CODE_BLOCK_PATTERN.split(docs)

                    for i in range(0, len(parts), 3):
                        # Text part
                        if i < len(parts):
                            text = parts[i].strip()
                            if text:
                                # Look for titles
                                lines = text.split('\n')
                                for line in lines:
                                    if line.startswith('TITLE:'):
                                        formatted_docs.append(f"**{line.replace('TITLE:', '').strip()}**")
                                    elif line.startswith('DESCRIPTION:'):
                                        formatted_docs.append(line.replace('DESCRIPTION:', '').strip())
                                    elif line.strip():
                                        formatted_docs.append(line)

                        # Code block
                        if i + 2 < len(parts):
                            language = parts[i + 1]
                            code = parts[i + 2]
                            formatted_docs.append(f"\n```{language}\n{code}```\n")

                    return "\n".join(formatted_docs)

            return ""

        except Context7TimeoutError:
            logger.error(f"Context7 timeout fetching docs for library: {library_id}")
            return ""
        except Exception as e:
            logger.error(f"Error fetching docs for library {library_id}: {e}", exc_info=True)
            return ""
