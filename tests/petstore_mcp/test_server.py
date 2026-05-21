"""Tests for server bootstrap."""

from types import SimpleNamespace

from petstore_mcp.config import Settings
from petstore_mcp.server import create_app


class _App:
    """FastMCP test double."""

    def __init__(self, _name: str) -> None:
        """Create app double.

        Args:
            _name: App name.

        Returns:
            None.
        """
        self.tool_calls: list[tuple[str, str]] = []
        self.resource_calls: list[str] = []

    def tool(self, name: str, description: str):
        """Store tool registration.

        Args:
            name: Tool name.
            description: Tool description.

        Returns:
            Handler decorator.
        """
        self.tool_calls.append((name, description))

        def decorator(func):
            return func

        return decorator

    def resource(self, uri: str):
        """Store resource registration.

        Args:
            uri: Resource URI.

        Returns:
            Handler decorator.
        """
        self.resource_calls.append(uri)

        def decorator(func):
            return func

        return decorator


def test_create_app_registers_components(monkeypatch) -> None:
    """Ensure app factory registers tools and resources.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    monkeypatch.setitem(
        __import__("sys").modules,
        "mcp.server.fastmcp",
        SimpleNamespace(FastMCP=_App),
    )
    app = create_app(Settings(request_timeout_seconds=1))
    assert app.tool_calls
    assert app.resource_calls
