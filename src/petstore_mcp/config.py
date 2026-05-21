"""Configuration management for the Petstore MCP server."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the MCP server.

    Attributes:
        api_base_url: Base URL for the Petstore API.
        api_key: Optional API key value sent as X-API-Key header.
        request_timeout_seconds: Timeout for outbound API requests.
        log_level: Python logging level.
    """

    model_config = SettingsConfigDict(
        env_prefix="PETSTORE_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    api_base_url: str = Field(default="https://petstore-api-dev.ramon-alcantara.work")
    api_key: str | None = Field(default=None)
    request_timeout_seconds: float = Field(default=10.0, gt=0)
    log_level: str = Field(default="INFO")
