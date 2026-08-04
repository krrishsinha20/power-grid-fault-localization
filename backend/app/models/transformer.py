from datetime import datetime

from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class Transformer(Base):
    __tablename__ = "transformers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    transformer_id: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False
    )

    feeder_id: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    pincode: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    poles = relationship(
        "Pole",
        back_populates="transformer",
        cascade="all, delete-orphan"
    )