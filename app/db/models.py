import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Pin(Base):
    __tablename__ = "pins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    admin1: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
