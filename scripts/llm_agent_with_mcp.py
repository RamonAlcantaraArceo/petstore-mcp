#!/usr/bin/env python3
"""LLM-backed MCP agent example using a local Ollama container.

The script asks an LLM to choose a Petstore MCP tool and arguments, then executes
that tool over MCP stdio.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SYSTEM_PROMPT = """You are a strict tool router for a Petstore MCP server.
Return only JSON with this shape:
{
    "tool": "health_check|pet_find_by_status|pet_get_by_id",
  "arguments": { ... },
  "reason": "short reason"
}

Rules:
- Use health_check for service health questions.
- Use pet_find_by_status with status in [available, pending, sold] for status queries.
- Use pet_get_by_id with pet_id integer for id queries.
- If no status is provided for a pet list request, use status=available.
- Never include markdown or extra keys.
"""


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the LLM-backed MCP agent."""
    parser = argparse.ArgumentParser(
        description="Use a local Ollama model to choose and execute a Petstore MCP tool."
    )
    parser.add_argument("prompt", help="Natural-language user request.")
    parser.add_argument(
        "--ollama-url",
        default=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        help="Base URL of the Ollama API (default: http://localhost:11434).",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
        help="Ollama model name (default: llama3.2:3b).",
    )
    parser.add_argument(
        "--llm-timeout",
        type=float,
        default=30.0,
        help="Timeout in seconds for the Ollama request.",
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


def _extract_first_json_object(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _fallback_route(prompt: str) -> tuple[str, dict[str, Any], str]:
    lowered = prompt.lower()
    pet_id_match = re.search(r"(?:pet\s*(?:id)?\s*|id\s+)(\d+)", lowered)
    if pet_id_match:
        pet_id = int(pet_id_match.group(1))
        return "pet_get_by_id", {"pet_id": pet_id}, "Fallback route: detected pet id."

    for status in ("available", "pending", "sold"):
        if status in lowered:
            return (
                "pet_find_by_status",
                {"status": status},
                f"Fallback route: detected status '{status}'.",
            )

    if any(keyword in lowered for keyword in ("health", "status", "alive", "ready")):
        return "health_check", {"include_details": True}, "Fallback route: health prompt."

    return (
        "pet_find_by_status",
        {"status": "available"},
        "Fallback route: defaulting to available pets.",
    )


def _normalize_plan(plan: dict[str, Any], prompt: str) -> tuple[str, dict[str, Any], str]:
    tool = plan.get("tool")
    arguments = plan.get("arguments")
    reason = plan.get("reason")

    if tool not in {"health_check", "pet_find_by_status", "pet_get_by_id"}:
        return _fallback_route(prompt)
    if not isinstance(arguments, dict):
        return _fallback_route(prompt)
    if not isinstance(reason, str):
        reason = "LLM route."

    if tool == "health_check":
        include = arguments.get("include_details", True)
        arguments = {"include_details": bool(include)}
    elif tool == "pet_find_by_status":
        status = str(arguments.get("status", "available")).lower()
        if status not in {"available", "pending", "sold"}:
            status = "available"
        arguments = {"status": status}
    elif tool == "pet_get_by_id":
        try:
            pet_id = int(arguments.get("pet_id"))
        except (TypeError, ValueError):
            return _fallback_route(prompt)
        arguments = {"pet_id": pet_id}

    return tool, arguments, reason


async def choose_tool_with_llm(
    *,
    prompt: str,
    ollama_url: str,
    model: str,
    timeout_seconds: float,
) -> tuple[str, dict[str, Any], str]:
    """Ask Ollama for a tool plan and normalize it into a safe tool call."""
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "prompt": (
            f"{SYSTEM_PROMPT}\n\n"
            f"User prompt:\n{prompt}\n\n"
            "Return only the JSON object."
        ),
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                f"{ollama_url.rstrip('/')}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        tool, arguments, reason = _fallback_route(prompt)
        return tool, arguments, f"LLM unavailable ({exc!r}); {reason}"

    raw_text = str(data.get("response", "")).strip()
    parsed = _extract_first_json_object(raw_text)
    if parsed is None:
        tool, arguments, reason = _fallback_route(prompt)
        return tool, arguments, f"LLM returned non-JSON; {reason}"

    return _normalize_plan(parsed, prompt)


async def run_agent(args: argparse.Namespace) -> int:
    """Execute one prompt by routing via LLM and calling the selected MCP tool."""
    tool_name, tool_args, reason = await choose_tool_with_llm(
        prompt=args.prompt,
        ollama_url=args.ollama_url,
        model=args.model,
        timeout_seconds=args.llm_timeout,
    )

    server = StdioServerParameters(
        command=args.server_command,
        args=args.server_args,
        env=dict(os.environ),
        cwd=os.getcwd(),
    )

    async with stdio_client(server) as (read_stream, write_stream), ClientSession(
        read_stream, write_stream
    ) as session:
        initialize = await session.initialize()
        print(
            f"Connected to MCP server: {initialize.serverInfo.name} "
            f"{initialize.serverInfo.version}"
        )
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
    """CLI entrypoint for the LLM-backed MCP agent example."""
    raise SystemExit(asyncio.run(run_agent(parse_args())))


if __name__ == "__main__":
    main()