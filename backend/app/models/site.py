import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    site_code: Mapped[str] = mapped_column(String(80), index=True, unique=True)
    site_name: Mapped[str] = mapped_column(String(200), index=True)
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    ground_elevation_m: Mapped[float] = mapped_column(Float, default=0.0)
    tower_height_m: Mapped[float] = mapped_column(Float, default=30.0)
    available_height_m: Mapped[float] = mapped_column(Float, default=30.0)
    overload: Mapped[int] = mapped_column(Integer, default=0)
    diverse_routing: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
