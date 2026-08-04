from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    Float,
    DateTime,
    JSON
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.database.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    # Business ID
    incident_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    # Fault Information
    fault_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    feeder_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    transformer_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    # ---------------------------------------
    # Fault Location
    # start_pole is NULL for Transformer Fault
    # ---------------------------------------
    start_pole: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    end_pole: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    # Impact
    affected_pole_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    affected_pole_ids: Mapped[list] = mapped_column(
        JSON,
        nullable=False
    )

    # Confidence
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    # Estimated Location
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

    # AI Output
    root_cause: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True
    )

    ai_summary: Mapped[str | None] = mapped_column(
        String(1500),
        nullable=True
    )

    recommended_action: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    # Workflow
    status: Mapped[str] = mapped_column(
        String(30),
        default="DETECTED"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # One Incident -> One Ticket
    ticket = relationship(
        "Ticket",
        back_populates="incident",
        uselist=False,
        cascade="all, delete-orphan"
    )