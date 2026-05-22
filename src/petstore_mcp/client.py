"""HTTP client utilities for the Petstore API."""

import logging
from collections.abc import Mapping
from typing import Any

import httpx

LOGGER = logging.getLogger(__name__)


class PetstoreClient:
    """Async Petstore API client.

    Args:
        base_url: Base URL for Petstore API requests.
        api_key: Optional API key sent via X-API-Key.
        timeout_seconds: Per-request timeout in seconds.
    """

    def __init__(self, base_url: str, api_key: str | None, timeout_seconds: float) -> None:
        """Initialize the API client.

        Args:
            base_url: API base URL.
            api_key: Optional API key.
            timeout_seconds: Timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> Any:
        """Perform an HTTP request against the Petstore API.

        Args:
            method: HTTP method name.
            path: Relative API path.
            params: Optional query parameters.
            json_body: Optional JSON body.

        Returns:
            Parsed JSON response.

        Raises:
            RuntimeError: If the request fails or returns invalid JSON.
        """
        headers: dict[str, str] = {}
        if self._api_key:
            headers["X-API-Key"] = self._api_key

        url = f"{self._base_url}/{path.lstrip('/')}"
        # Redact API key value for logs; show that it's present and its length.
        log_headers = {
            k: (f"<redacted len={len(v)}>" if k.lower() == "x-api-key" else v)
            for k, v in headers.items()
        }
        LOGGER.debug(
            "Petstore API outbound request: method=%s url=%s headers=%s params=%s",
            method,
            url,
            log_headers,
            params,
        )
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            LOGGER.exception("Petstore API request failed", extra={"path": path, "method": method})
            raise RuntimeError(f"Petstore API request failed: {method} {path}: {exc!r}") from exc

    async def get_health(self) -> dict[str, Any]:
        """Fetch the health payload.

        Returns:
            Parsed health response.
        """
        return await self.request("GET", "/health")

    async def find_pets_by_status(self, status: str) -> list[dict[str, Any]]:
        """Fetch pets by status value.

        Args:
            status: Target pet status.

        Returns:
            List of pet objects.
        """
        response = await self.request("GET", "/api/v1/pet/findByStatus", params={"status": status})
        return list(response)

    async def get_pet_by_id(self, pet_id: int) -> dict[str, Any]:
        """Fetch a pet by identifier.

        Args:
            pet_id: Target pet identifier.

        Returns:
            Pet object.
        """
        response = await self.request("GET", f"/api/v1/pet/{pet_id}")
        return dict(response)
