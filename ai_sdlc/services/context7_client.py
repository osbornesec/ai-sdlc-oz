"""Context7 client for fetching library documentation via SSE API."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Dict, List, Optional
from urllib.parse import urlencode

import httpx


class Context7Client:
    """Context7 client that properly handles SSE connections."""
    
    def __init__(self, base_url: str = "https://mcp.context7.com"):
        """Initialize Context7 client."""
        self.base_url = base_url
        self.timeout = httpx.Timeout(60.0, connect=10.0)
    
    async def _execute_tool(self, tool_name: str, parameters: Dict) -> Optional[Dict]:
        """Execute a Context7 tool via SSE API with proper session handling."""
        params = {"tool": tool_name}
        params.update(parameters)
        sse_url = f"{self.base_url}/sse?{urlencode(params)}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as sse_client:
            async with httpx.AsyncClient(timeout=self.timeout) as post_client:
                
                endpoint = None
                session_id = None
                result_queue = asyncio.Queue()
                
                async def sse_reader():
                    """Keep SSE connection alive and read data."""
                    async with sse_client.stream("GET", sse_url) as response:
                        async for line in response.aiter_lines():
                            await result_queue.put(line)
                            
                            if line.startswith("data: /messages"):
                                endpoint_data = line[6:]
                                await result_queue.put(("endpoint", endpoint_data))
                
                # Start SSE reader
                sse_task = asyncio.create_task(sse_reader())
                
                try:
                    # Wait for endpoint
                    while True:
                        item = await asyncio.wait_for(result_queue.get(), timeout=5.0)
                        
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
                    
                    post_response = await post_client.post(
                        messages_url,
                        json=request_data,
                        headers={
                            "Content-Type": "application/json",
                            "MCP-Session-Id": session_id
                        }
                    )
                    
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
                                        except json.JSONDecodeError:
                                            pass
                                elif "event: done" in str(line):
                                    break
                                    
                            except asyncio.TimeoutError:
                                break
                    
                    return None
                    
                except Exception:
                    # Error is logged at the public method level
                    return None
                finally:
                    if sse_task and not sse_task.done():
                        sse_task.cancel()
                        try:
                            await sse_task
                        except asyncio.CancelledError:
                            pass
    
    def _parse_library_results(self, text: str) -> List[Dict]:
        """Parse library results from Context7 text format."""
        results = []
        
        # Split by separator lines
        entries = text.split("----------")
        
        for entry in entries:
            if "Context7-compatible library ID:" in entry:
                result = {}
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
                        except:
                            pass
                    elif line.startswith("Trust Score:"):
                        try:
                            result["trustScore"] = float(line.replace("Trust Score:", "").strip())
                        except:
                            pass
                
                if "libraryId" in result:
                    results.append(result)
        
        return results
    
    def _parse_docs_content(self, response_data: Dict) -> str:
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
    
    def resolve_library_id(self, library_name: str) -> Optional[str]:
        """Resolve a library name to Context7 library ID."""
        try:
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            response_data = loop.run_until_complete(
                self._execute_tool("resolve-library-id", {"libraryName": library_name})
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
                                        score += min(lib.get("codeSnippetCount", 0) / 100, 10)
                                        
                                        if score > best_score:
                                            best_score = score
                                            best_match = lib
                                    
                                    if best_match:
                                        return best_match["libraryId"]
            
            return None
            
        except Exception:
            # Silently fail - calling code handles None return
            return None
        finally:
            loop.close()
    
    def get_library_docs(
        self, 
        library_id: str, 
        tokens: int = 5000,
        topic: Optional[str] = None
    ) -> str:
        """Get documentation for a library."""
        try:
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            args = {
                "context7CompatibleLibraryID": library_id,
                "tokens": tokens
            }
            if topic:
                args["topic"] = topic
            
            response_data = loop.run_until_complete(
                self._execute_tool("get-library-docs", args)
            )
            
            if response_data:
                docs = self._parse_docs_content(response_data)
                
                if docs:
                    # Format documentation
                    formatted_docs = []
                    
                    # Split by code blocks
                    parts = re.split(r'```(\w*)\n(.*?)```', docs, flags=re.DOTALL)
                    
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
            
        except Exception:
            # Silently fail - calling code handles empty return
            return ""
        finally:
            loop.close()
