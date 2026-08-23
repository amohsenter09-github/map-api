from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.services.map_client import MapClient

router = APIRouter(prefix="", tags=["map"])


def _location_from_geo(geo: dict) -> dict:
    return {
        "name": geo.get("name"),
        "country": geo.get("country"),
        "admin1": geo.get("admin1"),
        "latitude": geo.get("latitude"),
        "longitude": geo.get("longitude"),
    }


@router.get("/geocode")
async def geocode(city: str = Query(...)):
    settings = get_settings()
    client = MapClient(settings)
    try:
        results = await client.geocode_city(city)
        return {"results": [_location_from_geo(item) for item in results]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail="Upstream geocoding provider error") from e


@router.get("/map")
async def get_map(
    city: str | None = Query(default=None),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    zoom: int = Query(default=10, ge=1, le=18),
):
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
            latitude = float(geo["latitude"])
            longitude = float(geo["longitude"])
            location = _location_from_geo(geo)
        else:
            location = {"latitude": latitude, "longitude": longitude}

        return {
            "location": location,
            "viewport": client.viewport(latitude, longitude, zoom=zoom),  # type: ignore[arg-type]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail="Upstream geocoding provider error") from e
