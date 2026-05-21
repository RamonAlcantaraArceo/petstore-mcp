"""Tests for settings configuration."""

from petstore_mcp.config import Settings


def test_settings_defaults() -> None:
    """Validate default settings values.

    Returns:
        None.
    """
    settings = Settings()
    assert settings.api_base_url
    assert settings.request_timeout_seconds > 0
