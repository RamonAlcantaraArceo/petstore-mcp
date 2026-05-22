#!/usr/bin/env python3
"""Connect to the Petstore MCP server over stdio and call tools.

Examples:
  uv run python scripts/call_mcp_server.py --list
    uv run python scripts/call_mcp_server.py --tool health_check --arguments '{"include_details": true}'
    uv run python scripts/call_mcp_server.py --tool pet_find_by_status --arguments '{"status": "available"}'
    uv run python scripts/call_mcp_server.py --tool pet_get_by_id --arguments '{"pet_id": 1}'
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start the MCP server as a subprocess and interact with it over MCP stdio."
    )
    parser.add_argument(
        "--tool",
        default="health_check",
        help="Tool name to call after connecting (default: health_check).",
    )
    parser.add_argument(
        "--arguments",
        default='{"include_details": true}',
        help="JSON object of tool arguments.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List tools and resources without calling a tool.",
    )
    parser.add_argument(
        "--server-command",
        default="uv",
        help="Command used to start the MCP server subprocess (default: uv).",
    )
    parser.add_argument(
        "--server-args",
        nargs="*",
        default=["run", "petstore-mcp"],
        help="Arguments for the server command (default: run petstore-mcp).",
    )
    return parser.parse_args()


def load_arguments(raw_arguments: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON for --arguments: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SystemExit("--arguments must decode to a JSON object")
    return parsed


async def run_client(args: argparse.Namespace) -> int:
    server = StdioServerParameters(
        command=args.server_command,
        args=args.server_args,
        env=dict(os.environ),
        cwd=os.getcwd(),
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialize = await session.initialize()
            print(
                f"Connected to MCP server: {initialize.serverInfo.name} {initialize.serverInfo.version}"
            )

            tools = await session.list_tools()
            print("Tools:")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            resources = await session.list_resources()
            print("Resources:")
            for resource in resources.resources:
                print(f"- {resource.uri}")

            if args.list:
                return 0

            call_arguments = load_arguments(args.arguments)
            print(f"Calling tool: {args.tool}")
            print(f"Arguments: {json.dumps(call_arguments, indent=2)}")
            result = await session.call_tool(args.tool, call_arguments)

            print(f"isError: {result.isError}")
            if result.structuredContent is not None:
                print("Structured content:")
                print(json.dumps(result.structuredContent, indent=2))
            if result.content:
                print("Content:")
                for item in result.content:
                    if hasattr(item, "text"):
                        print(item.text)
                    else:
                        print(item)

            return 1 if result.isError else 0


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(run_client(args)))


if __name__ == "__main__":
    main()