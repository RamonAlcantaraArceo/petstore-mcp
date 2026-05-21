"""Tests for MCP resources."""

from typing import Any

import pytest

from petstore_mcp.resources import (
    ResourceContext,
    health_cached_resource,
    pets_paginated_resource,
    stream_pets_resource,
)


class _StubClient:
    """Client stub for resource tests."""

    async def get_health(self) -> dict[str, Any]:
        """Return health payload.

        Returns:
            Test health payload.
        """
        return {
            "status": "ok",
            "mode": "test",
            "details": {
                "version": "1",
                "build_date": "today",
                "git_commit_sha": "sha",
            },
        }

    async def find_pets_by_status(self, status: str) -> list[dict[str, Any]]:
        """Return fake pets list.

        Args:
            status: Requested status.

        Returns:
            Fake pets list.
        """
        return [{"id": index, "name": f"pet-{index}", "status": status} for index in range(1, 6)]


@pytest.mark.asyncio
async def test_health_resource_uses_cache() -> None:
    """Ensure cached health resource stores entries.

    Returns:
        None.
    """
    context = ResourceContext(client=_StubClient(), cache_ttl_seconds=60)
    first = await health_cached_resource(context)
    second = await health_cached_resource(context)
    assert first == second
    assert "health" in context.cache


@pytest.mark.asyncio
async def test_paginated_resource_returns_slice() -> None:
    """Ensure pagination output is correctly bounded.

    Returns:
        None.
    """
    context = ResourceContext(client=_StubClient())
    page = await pets_paginated_resource(context, status="available", page=2, page_size=2)
    assert page["page"] == 2
    assert len(page["items"]) == 2


@pytest.mark.asyncio
async def test_stream_resource_yields_pages() -> None:
    """Ensure streaming resource yields at least one page.

    Returns:
        None.
    """
    context = ResourceContext(client=_StubClient())
    chunks = [
        chunk async for chunk in stream_pets_resource(context, status="available", page_size=2)
    ]
    assert chunks
