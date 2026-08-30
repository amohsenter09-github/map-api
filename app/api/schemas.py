from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PinCreate(BaseModel):
    city: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    label: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def require_city_or_coords(self):
        city = (self.city or "").strip()
        if city:
            return self
        if self.latitude is None or self.longitude is None:
            raise ValueError("Provide city or latitude and longitude")
        return self


class PinOut(BaseModel):
    id: UUID
    label: str
    latitude: float
    longitude: float
    name: str | None
    country: str | None
    admin1: str | None
    address: str | None = None

    model_config = {"from_attributes": True}


class PinList(BaseModel):
    pins: list[PinOut]


class PinUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class NoteOut(BaseModel):
    id: UUID
    pin_id: UUID
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NoteList(BaseModel):
    notes: list[NoteOut]


class ActivityCreate(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    kind: str = Field(default="walk", max_length=40)


class ActivityPointCreate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    temperature: float | None = None
    windspeed: float | None = None
    weathercode: float | None = None
    us_aqi: float | None = None
    pm2_5: float | None = None


class ActivityPointOut(BaseModel):
    id: UUID
    latitude: float
    longitude: float
    temperature: float | None
    windspeed: float | None
    weathercode: float | None
    us_aqi: float | None
    pm2_5: float | None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class ActivityOut(BaseModel):
    id: UUID
    label: str
    kind: str
    started_at: datetime
    ended_at: datetime | None
    distance_m: float | None
    duration_s: float | None
    point_count: int = 0
    alerts: list[str] = []

    model_config = {"from_attributes": True}


class ActivityDetail(ActivityOut):
    points: list[ActivityPointOut] = []


class ActivityList(BaseModel):
    activities: list[ActivityOut]

