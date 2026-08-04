from datetime import datetime

from sqlalchemy import (
    String,
    Float,
    Integer,
    Boolean,
    ForeignKey,
    DateTime
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.database.database import Base


class Pole(Base):
    __tablename__ = "poles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    pole_id: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False
    )

    transformer_id: Mapped[int] = mapped_column(
        ForeignKey("transformers.id"),
        nullable=False
    )

    parent_pole_id: Mapped[int | None] = mapped_column(
        ForeignKey("poles.id"),
        nullable=True
    )

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    # NOTE: relaxed to nullable. Per the data contract, ~3% of real
    # pole registry rows have no pincode -- forcing this NOT NULL
    # would make it impossible to seed a realistic dataset, and would
    # hide the "pincode unknown" case the UI is supposed to surface
    # honestly instead of guessing.
    pincode: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True
    )

    energized: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Last heartbeat / telemetry received
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # -----------------------------------------------------------
    # Dedup / ordering bookkeeping, used by TelemetryService to
    # decide whether an incoming packet is newer evidence than what
    # we've already applied, per-device. `device_id` is NOT trusted
    # as a stable identity across the network (devices get swapped),
    # but within a single pole's history it tells us which device's
    # sequence counter we're currently tracking.
    #
    # NULL last_device_id also doubles as "this pole has no
    # telemetry device fitted" (~9% of the fleet) -- BoundaryDetector
    # and the confidence engine check this to decide whether a pole's
    # `energized` reading can be trusted as real evidence at all.
    # -----------------------------------------------------------
    last_device_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    last_applied_seq: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    transformer = relationship(
        "Transformer",
        back_populates="poles"
    )

    parent = relationship(
        "Pole",
        remote_side=[id]
    )

    telemetry = relationship(
        "Telemetry",
        back_populates="pole",
        cascade="all, delete-orphan"
    )