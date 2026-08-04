from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    DateTime
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.database.database import Base


class ScheduledOutage(Base):
    __tablename__ = "scheduled_outages"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    outage_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    feeder_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    transformer_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    end_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    reason: Mapped[str] = mapped_column(
        String(300),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE"
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