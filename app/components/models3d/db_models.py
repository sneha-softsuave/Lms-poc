"""Preloaded 3D model registry + hotspots (PRD 4.4).

The POC ships a FIXED library of 5 licence-clear models (admins associate a
model with a lesson but do not upload assets). Hotspots map a 3D point to a
named component + source_ref; selecting one drives the grounded component
explainer (reuses the chatbot).
"""

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Model3D(Base):
    __tablename__ = "models3d"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # e.g. engine-cutaway
    name: Mapped[str] = mapped_column(String(255))
    glb_uri: Mapped[str] = mapped_column(String(1024))  # served locally (MinIO/local), no CDN
    suitable_for: Mapped[str] = mapped_column(Text, default="")

    hotspots: Mapped[list["ModelHotspot"]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )


class ModelHotspot(Base):
    __tablename__ = "model_hotspots"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models3d.id", ondelete="CASCADE"), index=True)
    hotspot_key: Mapped[str] = mapped_column(String(64))
    component: Mapped[str] = mapped_column(String(255))
    position: Mapped[list] = mapped_column(JSON, default=list)  # [x, y, z]
    source_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    model: Mapped[Model3D] = relationship(back_populates="hotspots")
