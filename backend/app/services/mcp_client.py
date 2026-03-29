from __future__ import annotations

import json
import os
from typing import Any

import httpx


MCP_PROTOCOL_VERSION = "2025-03-26"
DEFAULT_MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")


class MCPClientError(RuntimeError):
    """Raised when the MCP server cannot be reached or returns an invalid response."""


class MCPToolExecutionError(RuntimeError):
    """Raised when an MCP tool reports an execution error."""


class MCPClient:
    def __init__(self, server_url: str | None = None, timeout: float = 30.0) -> None:
        self.server_url = (server_url or DEFAULT_MCP_SERVER_URL).rstrip("/")
        self.timeout = timeout
        self.session_id: str | None = None
        self.initialized = False

    async def list_tools(self) -> list[dict[str, Any]]:
        response = await self._request("tools/list")
        tools = response.get("tools")
        if not isinstance(tools, list):
            raise MCPClientError("MCP server returned an invalid tools/list response")
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments or {},
            },
        )
        if response.get("isError"):
            raise MCPToolExecutionError(self._flatten_tool_result(response))
        return response

    async def _request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        retry_on_session_expiry: bool = True,
    ) -> dict[str, Any]:
        if not self.initialized:
            await self._initialize()

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.server_url,
                headers=self._headers(include_session=True),
                json=payload,
            )

        if response.status_code == 404 and self.session_id and retry_on_session_expiry:
            self.initialized = False
            self.session_id = None
            return await self._request(method, params, retry_on_session_expiry=False)

        response.raise_for_status()
        result = self._parse_jsonrpc_response(response)
        if "error" in result:
            raise MCPClientError(result["error"].get("message", "Unknown MCP error"))
        return result.get("result", {})

    async def _initialize(self) -> None:
        initialize_error: Exception | None = None
        for candidate_url in self._candidate_urls():
            try:
                await self._initialize_once(candidate_url)
                self.server_url = candidate_url
                self.initialized = True
                return
            except httpx.HTTPStatusError as exc:  # pragma: no cover
                initialize_error = exc
                if exc.response.status_code not in {404, 405}:
                    break
            except Exception as exc:  # pragma: no cover
                initialize_error = exc
                break

        if isinstance(initialize_error, MCPClientError):
            raise initialize_error
        if initialize_error is not None:
            raise MCPClientError(str(initialize_error)) from initialize_error
        raise MCPClientError("MCP initialization failed")

    async def _initialize_once(self, server_url: str) -> None:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "aunalyticsNLSQL-backend",
                    "version": "1.0.0",
                },
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                server_url,
                headers=self._headers(include_session=False),
                json=payload,
            )
            response.raise_for_status()
            self.session_id = response.headers.get("Mcp-Session-Id") or response.headers.get("MCP-Session-Id")
            result = self._parse_jsonrpc_response(response)
            if "error" in result:
                raise MCPClientError(result["error"].get("message", "MCP initialize failed"))

            initialized_response = await client.post(
                server_url,
                headers=self._headers(include_session=True),
                json={
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                },
            )
            initialized_response.raise_for_status()

    def _candidate_urls(self) -> list[str]:
        if os.getenv("MCP_SERVER_URL"):
            return [self.server_url]
        if self.server_url.endswith("/mcp"):
            return [self.server_url, self.server_url[:-4]]
        return [self.server_url, f"{self.server_url}/mcp"]

    def _headers(self, *, include_session: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        }
        if include_session and self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _parse_jsonrpc_response(self, response: httpx.Response) -> dict[str, Any]:
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            return self._parse_sse_response(response.text)
        return response.json()

    @staticmethod
    def _parse_sse_response(raw_text: str) -> dict[str, Any]:
        data_lines: list[str] = []
        for line in raw_text.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())
        if not data_lines:
            raise MCPClientError("MCP server returned an empty SSE response")
        try:
            return json.loads("\n".join(data_lines))
        except json.JSONDecodeError as exc:
            raise MCPClientError("MCP server returned invalid SSE JSON") from exc

    @staticmethod
    def _flatten_tool_result(result: dict[str, Any]) -> str:
        content = result.get("content", [])
        if isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            if text_parts:
                return "\n".join(part for part in text_parts if part)
        structured = result.get("structuredContent")
        if structured is not None:
            return json.dumps(structured, ensure_ascii=False)
        return "Tool execution failed"
