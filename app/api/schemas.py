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

    model_config = {"from_attributes": True}


class PinList(BaseModel):
    pins: list[PinOut]
