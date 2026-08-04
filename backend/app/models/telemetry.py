from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.database.database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    pole_id: Mapped[int] = mapped_column(
        ForeignKey("poles.id"),
        nullable=False
    )

    device_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    event: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    energized: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )

    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    pole = relationship(
        "Pole",
        back_populates="telemetry"
    )
    