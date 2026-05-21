"""MCP resource registration and implementations."""

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from petstore_mcp.client import PetstoreClient

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CacheEntry:
    """A cache entry for resource results.

    Attributes:
        value: Cached payload.
        expires_at: Monotonic deadline.
    """

    value: dict[str, Any]
    expires_at: float


@dataclass(slots=True)
class ResourceContext:
    """Dependencies for resource handlers.

    Attributes:
        client: API client instance.
        cache_ttl_seconds: Time-to-live for cached resources.
        cache: Internal in-memory cache map.
    """

    client: PetstoreClient
    cache_ttl_seconds: float = 10.0
    cache: dict[str, CacheEntry] = field(default_factory=dict)


async def health_cached_resource(context: ResourceContext) -> dict[str, Any]:
    """Return a cached health payload.

    Args:
        context: Shared resource dependencies.

    Returns:
        Cached or freshly fetched health response.
    """
    key = "health"
    now = monotonic()
    cached = context.cache.get(key)
    if cached and cached.expires_at > now:
        return cached.value

    fresh = await context.client.get_health()
    context.cache[key] = CacheEntry(value=fresh, expires_at=now + context.cache_ttl_seconds)
    return fresh


async def pets_paginated_resource(
    context: ResourceContext,
    status: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Return a paginated pets response.

    Args:
        context: Shared resource dependencies.
        status: Status filter.
        page: 1-based page index.
        page_size: Number of items per page.

    Returns:
        Paginated payload with metadata.
    """
    items = await context.client.find_pets_by_status(status)
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return {
        "page": page,
        "page_size": page_size,
        "total": len(items),
        "items": items[start:end],
    }


async def stream_pets_resource(
    context: ResourceContext,
    status: str,
    page_size: int,
) -> AsyncIterator[dict[str, Any]]:
    """Yield pets as streaming pages.

    Args:
        context: Shared resource dependencies.
        status: Status filter.
        page_size: Number of items per streamed page.

    Returns:
        Async iterator of page payloads.
    """
    page = 1
    while True:
        payload = await pets_paginated_resource(
            context,
            status=status,
            page=page,
            page_size=page_size,
        )
        if not payload["items"]:
            break
        yield payload
        page += 1
        await asyncio.sleep(0)


def register_resources(app: Any, context: ResourceContext) -> None:
    """Register resources in the MCP application.

    Args:
        app: MCP app instance exposing `resource` decorator.
        context: Shared resource dependencies.

    Returns:
        None.
    """

    @app.resource("resource://health/cached")
    async def health_cached() -> dict[str, Any]:
        """Expose cached health details as a resource.

        Returns:
            Cached health payload.
        """
        return await health_cached_resource(context)

    @app.resource("resource://pets/paginated/{status}/{page}/{page_size}")
    async def pets_paginated(status: str, page: int, page_size: int) -> dict[str, Any]:
        """Expose paginated pets resource.

        Args:
            status: Status filter.
            page: Page number.
            page_size: Number of pets per page.

        Returns:
            Paginated pets payload.
        """
        return await pets_paginated_resource(context, status=status, page=page, page_size=page_size)

    @app.resource("resource://pets/stream/{status}/{page_size}")
    async def pets_stream(status: str, page_size: int) -> list[dict[str, Any]]:
        """Expose streaming-style pets pages.

        Args:
            status: Status filter.
            page_size: Page size.

        Returns:
            Materialized stream of page payloads.
        """
        result: list[dict[str, Any]] = []
        async for chunk in stream_pets_resource(context, status=status, page_size=page_size):
            result.append(chunk)
        return result
