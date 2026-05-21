"""Server bootstrap for Petstore MCP."""

import logging
from typing import Any

from petstore_mcp.client import PetstoreClient
from petstore_mcp.config import Settings
from petstore_mcp.logging_config import configure_logging
from petstore_mcp.resources import ResourceContext, register_resources
from petstore_mcp.tools import ToolContext, register_tools

LOGGER = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, client: PetstoreClient | None = None) -> Any:
    """Create and configure the MCP server application.

    Args:
        settings: Optional explicit settings instance.
        client: Optional explicit API client instance.

    Returns:
        Configured FastMCP application instance.
    """
    from mcp.server.fastmcp import FastMCP

    resolved_settings = settings or Settings()
    configure_logging(resolved_settings.log_level)

    resolved_client = client or PetstoreClient(
        base_url=resolved_settings.api_base_url,
        api_key=resolved_settings.api_key,
        timeout_seconds=resolved_settings.request_timeout_seconds,
    )

    app = FastMCP("petstore-mcp")
    register_tools(
        app,
        ToolContext(
            client=resolved_client,
            timeout_seconds=resolved_settings.request_timeout_seconds,
        ),
    )
    register_resources(app, ResourceContext(client=resolved_client))
    LOGGER.info("Petstore MCP application initialized")
    return app


def run() -> None:
    """Run the MCP server process.

    Returns:
        None.
    """
    app = create_app()
    try:
        app.run()
    except KeyboardInterrupt:
        LOGGER.info("Petstore MCP server shutdown requested")
