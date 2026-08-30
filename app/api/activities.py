import logging
import math
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    ActivityCreate,
    ActivityDetail,
    ActivityList,
    ActivityOut,
    ActivityPointCreate,
    ActivityPointOut,
)
from app.core.config import get_settings
from app.db.models import Activity, ActivityPoint
from app.db.session import get_session
from app.services.conditions_client import ConditionsClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["activities"])

_EARTH_M = 6371000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_M * math.asin(min(1.0, math.sqrt(a)))


def _alerts_for(points: list[ActivityPoint]) -> list[str]:
    alerts: list[str] = []
    aqi_vals = [p.us_aqi for p in points if p.us_aqi is not None]
    wind_vals = [p.windspeed for p in points if p.windspeed is not None]
    temp_vals = [p.temperature for p in points if p.temperature is not None]
    if aqi_vals and max(aqi_vals) > 100:
        alerts.append(f"US AQI reached {max(aqi_vals):.0f} (unhealthy for sensitive groups)")
    if wind_vals and max(wind_vals) > 40:
        alerts.append(f"Wind reached {max(wind_vals):.0f} km/h")
    if temp_vals and min(temp_vals) < 0:
        alerts.append(f"Temperature dropped to {min(temp_vals):.1f}°")
    return alerts


def _to_out(activity: Activity, points: list[ActivityPoint] | None = None) -> ActivityOut:
    pts = points if points is not None else list(activity.points or [])
    return ActivityOut(
        id=activity.id,
        label=activity.label,
        kind=activity.kind,
        started_at=activity.started_at,
        ended_at=activity.ended_at,
        distance_m=activity.distance_m,
        duration_s=activity.duration_s,
        point_count=len(pts),
        alerts=_alerts_for(pts),
    )


async def _load_activity(session: AsyncSession, activity_id: UUID) -> Activity:
    result = await session.execute(
        select(Activity).options(selectinload(Activity.points)).where(Activity.id == activity_id)
    )
    activity = result.scalar_one_or_none()
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.post("/activities", status_code=201, response_model=ActivityOut)
async def start_activity(body: ActivityCreate, session: AsyncSession = Depends(get_session)):
    kind = (body.kind or "walk").strip().lower() or "walk"
    label = (body.label or "").strip() or kind.title()
    activity = Activity(label=label, kind=kind)
    session.add(activity)
    await session.commit()
    await session.refresh(activity)
    return _to_out(activity, [])


@router.get("/activities", response_model=ActivityList)
async def list_activities(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Activity).options(selectinload(Activity.points)).order_by(Activity.started_at.desc())
    )
    activities = list(result.scalars().unique().all())
    return ActivityList(activities=[_to_out(item, list(item.points)) for item in activities])


@router.get("/activities/{activity_id}", response_model=ActivityDetail)
async def get_activity(activity_id: UUID, session: AsyncSession = Depends(get_session)):
    activity = await _load_activity(session, activity_id)
    points = list(activity.points)
    base = _to_out(activity, points)
    return ActivityDetail(**base.model_dump(), points=points)


@router.post("/activities/{activity_id}/points", status_code=201, response_model=ActivityPointOut)
async def add_point(
    activity_id: UUID,
    body: ActivityPointCreate,
    session: AsyncSession = Depends(get_session),
):
    activity = await _load_activity(session, activity_id)
    if activity.ended_at is not None:
        raise HTTPException(status_code=409, detail="Activity already stopped")

    sample = {
        "temperature": body.temperature,
        "windspeed": body.windspeed,
        "weathercode": body.weathercode,
        "us_aqi": body.us_aqi,
        "pm2_5": body.pm2_5,
    }
    if all(value is None for value in sample.values()):
        try:
            sample.update(await ConditionsClient(get_settings()).sample(body.latitude, body.longitude))
        except Exception:
            logger.exception("Could not enrich activity point with live conditions")

    points = list(activity.points)
    extra = 0.0
    if points:
        last = points[-1]
        extra = haversine_m(last.latitude, last.longitude, body.latitude, body.longitude)
    activity.distance_m = (activity.distance_m or 0.0) + extra

    point = ActivityPoint(
        activity_id=activity.id,
        latitude=body.latitude,
        longitude=body.longitude,
        temperature=sample.get("temperature"),
        windspeed=sample.get("windspeed"),
        weathercode=sample.get("weathercode"),
        us_aqi=sample.get("us_aqi"),
        pm2_5=sample.get("pm2_5"),
    )
    session.add(point)
    await session.commit()
    await session.refresh(point)
    return point


@router.post("/activities/{activity_id}/stop", response_model=ActivityDetail)
async def stop_activity(activity_id: UUID, session: AsyncSession = Depends(get_session)):
    activity = await _load_activity(session, activity_id)
    if activity.ended_at is None:
        now = datetime.now(timezone.utc)
        activity.ended_at = now
        started = activity.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        activity.duration_s = max(0.0, (now - started).total_seconds())
        await session.commit()
        activity = await _load_activity(session, activity_id)
    points = list(activity.points)
    base = _to_out(activity, points)
    return ActivityDetail(**base.model_dump(), points=points)


@router.delete("/activities/{activity_id}", status_code=204)
async def delete_activity(activity_id: UUID, session: AsyncSession = Depends(get_session)):
    activity = await session.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    await session.delete(activity)
    await session.commit()
