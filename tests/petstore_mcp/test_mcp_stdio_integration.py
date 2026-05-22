"""Integration tests for live MCP stdio interaction."""

import json
import os
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class _PetstoreHandler(BaseHTTPRequestHandler):
    """Minimal Petstore API used by MCP integration tests."""

    api_key = "integration-key"

    def log_message(self, message: str, *args: object) -> None:
        del message, args

    def _write_json(self, status_code: int, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _is_authorized(self) -> bool:
        return self.headers.get("X-API-Key") == self.api_key

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._write_json(
                200,
                {
                    "status": "ok",
                    "mode": "test",
                    "details": {
                        "version": "test-version",
                        "build_date": "today",
                        "git_commit_sha": "abc123",
                    },
                },
            )
            return

        if not self._is_authorized():
            self._write_json(401, {"detail": "Unauthorized"})
            return

        if parsed.path == "/api/v1/pet/findByStatus":
            query = parse_qs(parsed.query)
            status = query.get("status", ["available"])[0]
            self._write_json(200, [{"id": 1, "name": "Fluffy", "status": status}])
            return

        if parsed.path == "/api/v1/pet/1":
            self._write_json(200, {"id": 1, "name": "Fluffy", "status": "available"})
            return

        self._write_json(404, {"detail": "Not found"})


@contextmanager
def _run_petstore_api() -> str:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _PetstoreHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_mcp_stdio_client_can_call_live_server_tools() -> None:
    """Launch the MCP server and call its tools over stdio."""
    with _run_petstore_api() as api_base_url:
        env = dict(os.environ)
        env.update(
            {
                "PETSTORE_MCP_API_BASE_URL": api_base_url,
                "PETSTORE_MCP_API_KEY": _PetstoreHandler.api_key,
                "PETSTORE_MCP_LOG_LEVEL": "ERROR",
            }
        )
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "petstore_mcp"],
            env=env,
            cwd=_repo_root(),
        )

        async with stdio_client(server) as (read_stream, write_stream), ClientSession(
            read_stream, write_stream
        ) as session:
            initialize = await session.initialize()
            assert initialize.serverInfo.name == "petstore-mcp"

            tools = await session.list_tools()
            tool_by_name = {tool.name: tool for tool in tools.tools}
            assert set(tool_by_name) == {
                "health_check",
                "pet_find_by_status",
                "pet_get_by_id",
            }
            assert "kwargs" not in tool_by_name["health_check"].inputSchema.get(
                "properties", {}
            )
            assert "include_details" in tool_by_name["health_check"].inputSchema.get(
                "properties", {}
            )
            assert "status" in tool_by_name["pet_find_by_status"].inputSchema.get(
                "properties", {}
            )
            assert "pet_id" in tool_by_name["pet_get_by_id"].inputSchema.get(
                "properties", {}
            )

            health = await session.call_tool("health_check", {"include_details": True})
            assert health.isError is False
            assert "\"status\": \"ok\"" in health.content[0].text

            pets = await session.call_tool(
                "pet_find_by_status", {"status": "available"}
            )
            assert pets.isError is False
            assert "Fluffy" in pets.content[0].text

            pet = await session.call_tool("pet_get_by_id", {"pet_id": 1})
            assert pet.isError is False
            assert "\"id\": 1" in pet.content[0].text