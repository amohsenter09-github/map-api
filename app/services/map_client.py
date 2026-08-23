from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings


class MapClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._timeout = httpx.Timeout(settings.http_timeout_seconds)
        self._user_agent = f"{settings.app_name}/1.0"

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
        url = f"{self._settings.nominatim_base_url.rstrip('/')}/reverse"
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "jsonv2",
            "addressdetails": 1,
        }
        headers = {"User-Agent": self._user_agent, "Accept-Language": "en"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        address = data.get("address") or {}
        name = data.get("name") or address.get("city") or address.get("town") or address.get("village")
        if not name and not address:
            raise ValueError(f"Location not found: {latitude},{longitude}")
        return {
            "name": name,
            "country": address.get("country"),
            "admin1": address.get("state") or address.get("region"),
            "latitude": float(data.get("lat", latitude)),
            "longitude": float(data.get("lon", longitude)),
        }

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
