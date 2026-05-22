#!/usr/bin/env python3
"""Validate MCP wiring by calling the Petstore API and invoking local tool handlers.

Usage:
  uv run python scripts/validate_mcp.py
  python scripts/validate_mcp.py --api-base-url http://localhost:8000 --api-key yourkey --timeout 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import traceback
from typing import Any

from petstore_mcp.client import PetstoreClient
from petstore_mcp.tools import register_tools, ToolContext
from petstore_mcp.config import Settings


class _AppStub:
    """Minimal app stub that records handlers (same pattern as tests)."""

    def __init__(self) -> None:
        self.handlers: dict[str, Any] = {}

    def tool(self, name: str, description: str):
        del description

        def decorator(func: Any) -> Any:
            self.handlers[name] = func
            return func

        return decorator


def _print_hint_for_error(exc: Exception) -> None:
    """Print actionable hints for common runtime failures."""
    message = str(exc)
    if "401" in message or "Unauthorized" in message:
        print(
            "HINT: Pet endpoints require auth. Set PETSTORE_MCP_API_KEY or pass --api-key."
        )
    if "ConnectError" in message or "All connection attempts failed" in message:
        print(
            "HINT: Verify PETSTORE_MCP_API_BASE_URL points to a reachable Petstore API instance."
        )


async def run_checks(api_base_url: str, api_key: str | None, timeout: float) -> int:
    print(f"Using Petstore API base: {api_base_url}")
    print("Note: this script validates tool wiring + API connectivity, not MCP network transport.")
    client = PetstoreClient(base_url=api_base_url, api_key=api_key, timeout_seconds=timeout)

    try:
        print("\n-> Petstore API: GET /health")
        health = await client.get_health()
        print(json.dumps(health, indent=2))
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        print("ERROR: Petstore API health check failed:", exc)
        _print_hint_for_error(exc)
        traceback.print_exc()
        return 2

    context = ToolContext(client=client, timeout_seconds=timeout)
    app = _AppStub()
    register_tools(app, context)

    print("\nRegistered tools:", list(app.handlers.keys()))

    # Invoke the main tool handlers to validate end-to-end wiring
    try:
        print("\nInvoking tool: health_check")
        payload = await app.handlers["health_check"]()
        print(json.dumps(payload, indent=2))
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        print("ERROR: health_check failed:", exc)
        _print_hint_for_error(exc)
        traceback.print_exc()
        return 3

    try:
        print("\nInvoking tool: pet_find_by_status (defaults)")
        payload = await app.handlers["pet_find_by_status"]()
        print(json.dumps(payload, indent=2))
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        print("ERROR: pet_find_by_status failed:", exc)
        _print_hint_for_error(exc)
        traceback.print_exc()
        return 4

    try:
        print("\nInvoking tool: pet_get_by_id (pet_id=1)")
        payload = await app.handlers["pet_get_by_id"](pet_id=1)
        print(json.dumps(payload, indent=2))
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        print("ERROR: pet_get_by_id failed:", exc)
        _print_hint_for_error(exc)
        traceback.print_exc()
        return 5

    print("\nAll checks passed.")
    return 0


def parse_args() -> argparse.Namespace:
    s = Settings()
    parser = argparse.ArgumentParser(description="Validate Petstore MCP wiring and API connectivity.")
    parser.add_argument("--api-base-url", help=f"Petstore API base URL (default: {s.api_base_url})")
    parser.add_argument("--api-key", help="Petstore API key (optional)")
    parser.add_argument("--timeout", type=float, default=s.request_timeout_seconds, help=f"Per-request timeout in seconds (default: {s.request_timeout_seconds})")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_base_url = args.api_base_url or os.environ.get("PETSTORE_MCP_API_BASE_URL") or Settings().api_base_url
    api_key = args.api_key or os.environ.get("PETSTORE_MCP_API_KEY")
    timeout = float(args.timeout)

    rc = asyncio.run(run_checks(api_base_url, api_key, timeout))
    sys.exit(rc)


if __name__ == "__main__":
    main()
