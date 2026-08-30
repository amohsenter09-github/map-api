from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class ConditionsClient:
    """Live weather + air quality at a coordinate (Open-Meteo, same sources as the sibling APIs)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._timeout = httpx.Timeout(settings.http_timeout_seconds)

    async def sample(self, latitude: float, longitude: float) -> dict[str, Any]:
        weather, air = await asyncio.gather(
            self._weather(latitude, longitude),
            self._air_quality(latitude, longitude),
            return_exceptions=True,
        )
        out: dict[str, Any] = {}
        if isinstance(weather, dict):
            out.update(weather)
        elif isinstance(weather, Exception):
            logger.warning("Weather sample failed: %s", weather)
        if isinstance(air, dict):
            out.update(air)
        elif isinstance(air, Exception):
            logger.warning("Air quality sample failed: %s", air)
        return out

    async def _weather(self, latitude: float, longitude: float) -> dict[str, Any]:
        url = f"{self._settings.open_meteo_base_url.rstrip('/')}/forecast"
        params = {"latitude": latitude, "longitude": longitude, "current_weather": True}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            current = resp.json().get("current_weather") or {}
        return {
            "temperature": current.get("temperature"),
            "windspeed": current.get("windspeed"),
            "weathercode": current.get("weathercode"),
        }

    async def _air_quality(self, latitude: float, longitude: float) -> dict[str, Any]:
        url = f"{self._settings.open_meteo_air_quality_base_url.rstrip('/')}/air-quality"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "us_aqi,pm2_5",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            current = resp.json().get("current") or {}
        return {
            "us_aqi": current.get("us_aqi"),
            "pm2_5": current.get("pm2_5"),
        }
