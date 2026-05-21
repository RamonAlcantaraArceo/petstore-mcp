"""Logging utilities for the Petstore MCP server."""

import logging


def configure_logging(level: str) -> None:
    """Configure structured-like logging output.

    Args:
        level: Desired logging level name.

    Returns:
        None.
    """
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
