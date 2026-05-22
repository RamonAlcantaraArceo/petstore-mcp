"""Tests for MCP tool registration and execution."""

from collections.abc import Callable
from typing import Any

import pytest

from petstore_mcp.schemas import GetPetByIdInput
from petstore_mcp.tools import TOOL_REGISTRY, ToolContext, register_tools


class _StubClient:
    """Test client implementation for tools."""

    async def get_health(self) -> dict[str, Any]:
        """Return mock health response.

        Returns:
            Mocked payload.
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
        """Return mock pets list.

        Args:
            status: Input status value.

        Returns:
            Mocked pets.
        """
        return [{"id": 1, "name": "Fluffy", "status": status}]

    async def get_pet_by_id(self, pet_id: int) -> dict[str, Any]:
        """Return mock pet.

        Args:
            pet_id: Pet identifier.

        Returns:
            Mocked pet object.
        """
        return {"id": pet_id, "name": "Fluffy", "status": "available"}


class _AppStub:
    """Application test double for registration APIs."""

    def __init__(self) -> None:
        """Initialize app stub."""
        self.handlers: dict[str, Callable[..., Any]] = {}

    def tool(
        self,
        name: str,
        description: str,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a handler callback.

        Args:
            name: Tool name.
            description: Tool description.

        Returns:
            Decorator for handlers.
        """
        del description

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.handlers[name] = func
            return func

        return decorator


@pytest.mark.asyncio
async def test_register_tools_binds_handlers() -> None:
    """Validate tool registration count.

    Returns:
        None.
    """
    app = _AppStub()
    register_tools(app, ToolContext(client=_StubClient(), timeout_seconds=1))
    assert len(app.handlers) == len(TOOL_REGISTRY)


@pytest.mark.asyncio
async def test_tool_handler_returns_valid_payload() -> None:
    """Validate a registered tool response.

    Returns:
        None.
    """
    app = _AppStub()
    register_tools(app, ToolContext(client=_StubClient(), timeout_seconds=1))
    payload = await app.handlers["pet_get_by_id"](**GetPetByIdInput(pet_id=7).model_dump())
    assert payload["id"] == 7
