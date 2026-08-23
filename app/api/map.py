import logging

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.services.map_client import MapClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["map"])


def _normalize_city(city: str | None) -> str | None:
    if city is None:
        return None
    city = city.strip()
    return city or None


def _location_from_geo(geo: dict) -> dict:
    return {
        "name": geo.get("name"),
        "country": geo.get("country"),
        "admin1": geo.get("admin1"),
        "latitude": geo.get("latitude"),
        "longitude": geo.get("longitude"),
    }


@router.get("/geocode")
async def geocode(city: str = Query(..., min_length=1)):
    city = city.strip()
    if not city:
        raise HTTPException(status_code=400, detail="city must not be empty")

    settings = get_settings()
    client = MapClient(settings)
    try:
        results = await client.geocode_city(city)
        return {"results": [_location_from_geo(item) for item in results]}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except httpx.HTTPError as e:
        logger.exception("Upstream geocoding provider error")
        raise HTTPException(status_code=502, detail="Upstream geocoding provider error") from e


@router.get("/reverse")
async def reverse(
    latitude: float = Query(...),
    longitude: float = Query(...),
):
    settings = get_settings()
    client = MapClient(settings)
    try:
        geo = await client.reverse_geocode(latitude, longitude)
        return {"location": _location_from_geo(geo)}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except httpx.HTTPError as e:
        logger.exception("Upstream reverse geocoding provider error")
        raise HTTPException(status_code=502, detail="Upstream reverse geocoding provider error") from e


@router.get("/map")
async def get_map(
    city: str | None = Query(default=None),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    zoom: int = Query(default=10, ge=1, le=18),
):
    city = _normalize_city(city)
    if city is None and (latitude is None or longitude is None):
        raise HTTPException(
            status_code=400,
            detail="Provide either city=... or latitude=...&longitude=...",
        )

    settings = get_settings()
    client = MapClient(settings)

    try:
        if city is not None:
            geo = (await client.geocode_city(city, count=1))[0]
            resolved_lat = float(geo["latitude"])
            resolved_lon = float(geo["longitude"])
            location = _location_from_geo(geo)
        else:
            resolved_lat = float(latitude)
            resolved_lon = float(longitude)
            location = {"latitude": resolved_lat, "longitude": resolved_lon}

        return {
            "location": location,
            "viewport": client.viewport(resolved_lat, resolved_lon, zoom=zoom),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except httpx.HTTPError as e:
        logger.exception("Upstream geocoding provider error")
        raise HTTPException(status_code=502, detail="Upstream geocoding provider error") from e
