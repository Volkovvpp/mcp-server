import httpx
import logging
import time
from typing import Any, Dict, Optional

from src.core.config import settings
from src.core.exceptions import UpstreamApiError

logger = logging.getLogger("discovery_client")

class DiscoveryApiClient:
    def __init__(self, api_key: Optional[str] = None, timeout: Optional[float] = None):
        self._api_key = api_key
        self._base_url = settings.BASE_URL
        self._timeout = timeout or settings.TIMEOUT

        self._headers = {
            "Accept": "application/json",
            "User-Agent": "mcp-travel-server/1.0",
        }
        if self._api_key:
            self._headers["Authorization"] = self._api_key

        self._client = httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=self._timeout)

    async def close(self):
        await self._client.aclose()

    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start_time = time.monotonic()
        try:
            response = await self._client.request(method, endpoint, params=params)
            latency = round(time.monotonic() - start_time, 3)
            logger.info(f"Request {method} {response.url} completed in {latency}s with status {response.status_code}")

            if response.status_code >= 400:
                msg = f"HTTP error {response.status_code} for endpoint {endpoint}: {response.text}"
                logger.error(msg)
                raise UpstreamApiError(msg)

            return response.json()

        except httpx.RequestError as exc:
            msg = f"Network error when accessing {endpoint}: {exc}"
            logger.error(msg)
            raise UpstreamApiError(msg) from exc

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self._make_request("GET", endpoint, params=params)
