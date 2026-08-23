from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings


class MapClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._timeout = httpx.Timeout(settings.http_timeout_seconds)

    async def geocode_city(self, city: str, count: int = 5) -> list[dict[str, Any]]:
        url = f"{self._settings.open_meteo_geocoding_base_url.rstrip('/')}/search"
        params = {"name": city, "count": count, "language": "en", "format": "json"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results") or []
        if not results:
            raise ValueError(f"City not found: {city}")
        return results

    async def reverse_geocode(self, latitude: float, longitude: float) -> dict[str, Any]:
        url = f"{self._settings.open_meteo_geocoding_base_url.rstrip('/')}/reverse"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "language": "en",
            "format": "json",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results") or []
        if not results:
            raise ValueError(f"Location not found: {latitude},{longitude}")
        return results[0]

    @staticmethod
    def viewport(latitude: float, longitude: float, zoom: int = 10) -> dict[str, Any]:
        delta = max(0.05, 1.5 / zoom)
        return {
            "center": {"latitude": latitude, "longitude": longitude},
            "zoom": zoom,
            "bounding_box": {
                "south": latitude - delta,
                "north": latitude + delta,
                "west": longitude - delta,
                "east": longitude + delta,
            },
        }
