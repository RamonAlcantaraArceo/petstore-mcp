"""CLI entrypoint for Petstore MCP server."""

from petstore_mcp.server import run


def main() -> None:
    """Start the MCP server.

    Returns:
        None.
    """
    run()


if __name__ == "__main__":
    main()
