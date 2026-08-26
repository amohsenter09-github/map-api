import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PinCreate, PinList, PinOut
from app.core.config import get_settings
from app.db.models import Pin
from app.db.session import get_session
from app.services.map_client import MapClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pins"])


def _label_from(create: PinCreate, name: str | None, city: str | None) -> str:
    if create.label and create.label.strip():
        return create.label.strip()
    if name:
        return name
    if city:
        return city.strip()
    return f"{create.latitude},{create.longitude}"


@router.post("/pins", status_code=201, response_model=PinOut)
async def create_pin(body: PinCreate, session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    client = MapClient(settings)
    city = (body.city or "").strip() or None
    name = country = admin1 = None
    try:
        if city:
            geo = (await client.geocode_city(city, count=1))[0]
            lat = float(geo["latitude"])
            lon = float(geo["longitude"])
            name = geo.get("name")
            country = geo.get("country")
            admin1 = geo.get("admin1")
        else:
            lat = float(body.latitude)
            lon = float(body.longitude)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except httpx.HTTPError as e:
        logger.exception("Upstream geocoding provider error")
        raise HTTPException(status_code=502, detail="Upstream geocoding provider error") from e

    pin = Pin(
        label=_label_from(body, name, city),
        latitude=lat,
        longitude=lon,
        name=name,
        country=country,
        admin1=admin1,
    )
    session.add(pin)
    await session.commit()
    await session.refresh(pin)
    return pin


@router.get("/pins", response_model=PinList)
async def list_pins(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Pin).order_by(Pin.created_at.desc()))
    return PinList(pins=list(result.scalars().all()))


@router.get("/pins/{pin_id}", response_model=PinOut)
async def get_pin(pin_id: UUID, session: AsyncSession = Depends(get_session)):
    pin = await session.get(Pin, pin_id)
    if pin is None:
        raise HTTPException(status_code=404, detail="Pin not found")
    return pin


@router.delete("/pins/{pin_id}", status_code=204)
async def delete_pin(pin_id: UUID, session: AsyncSession = Depends(get_session)):
    pin = await session.get(Pin, pin_id)
    if pin is None:
        raise HTTPException(status_code=404, detail="Pin not found")
    await session.delete(pin)
    await session.commit()


@router.post("/pins/{pin_id}/reverse", response_model=PinOut)
async def reverse_pin(pin_id: UUID, session: AsyncSession = Depends(get_session)):
    pin = await session.get(Pin, pin_id)
    if pin is None:
        raise HTTPException(status_code=404, detail="Pin not found")
    settings = get_settings()
    client = MapClient(settings)
    try:
        geo = await client.reverse_geocode(pin.latitude, pin.longitude)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except httpx.HTTPError as e:
        logger.exception("Upstream reverse geocoding provider error")
        raise HTTPException(status_code=502, detail="Upstream reverse geocoding provider error") from e
    pin.name = geo.get("name")
    pin.country = geo.get("country")
    pin.admin1 = geo.get("admin1")
    if not pin.label:
        pin.label = pin.name or pin.label
    await session.commit()
    await session.refresh(pin)
    return pin
