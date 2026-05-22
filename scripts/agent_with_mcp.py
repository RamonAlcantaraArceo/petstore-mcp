#!/usr/bin/env python3
"""Small prompt-driven example that selects an MCP tool and calls the server."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Choose a Petstore MCP tool from a plain-language prompt and call it."
    )
    parser.add_argument("prompt", help="Natural-language prompt to route to a Petstore MCP tool.")
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


def choose_tool(prompt: str) -> tuple[str, dict[str, Any], str]:
    lowered = prompt.lower()

    pet_id_match = re.search(r"(?:pet\s*(?:id)?\s*|id\s+)(\d+)", lowered)
    if pet_id_match:
        pet_id = int(pet_id_match.group(1))
        return "pet_get_by_id", {"pet_id": pet_id}, f"Detected pet identifier {pet_id}."

    for status in ("available", "pending", "sold"):
        if status in lowered:
            return (
                "pet_find_by_status",
                {"status": status},
                f"Detected pet status filter '{status}'.",
            )

    if any(keyword in lowered for keyword in ("health", "status", "alive", "ready")):
        return "health_check", {"include_details": True}, "Detected health-style prompt."

    if "pet" in lowered or "pets" in lowered:
        return (
            "pet_find_by_status",
            {"status": "available"},
            "Detected generic pet query; defaulting to available pets.",
        )

    raise SystemExit(
        "Could not choose a tool from the prompt. Mention health, a pet id, or a pet status."
    )


async def run_agent(args: argparse.Namespace) -> int:
    tool_name, tool_args, reason = choose_tool(args.prompt)
    server = StdioServerParameters(
        command=args.server_command,
        args=args.server_args,
        env=dict(os.environ),
        cwd=os.getcwd(),
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialize = await session.initialize()
            print(f"Connected to MCP server: {initialize.serverInfo.name} {initialize.serverInfo.version}")
            print(f"Prompt: {args.prompt}")
            print(f"Decision: {reason}")
            print(f"Calling tool: {tool_name}")
            print(f"Arguments: {json.dumps(tool_args, indent=2)}")
            result = await session.call_tool(tool_name, tool_args)
            print(f"isError: {result.isError}")
            if result.content:
                print("Content:")
                for item in result.content:
                    print(getattr(item, "text", item))
            return 1 if result.isError else 0


def main() -> None:
    raise SystemExit(asyncio.run(run_agent(parse_args())))


if __name__ == "__main__":
    main()