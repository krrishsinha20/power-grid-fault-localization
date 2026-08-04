from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.database.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    # Business ID
    ticket_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    # Incident Reference
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id"),
        nullable=False,
        unique=True
    )

    # Assignment
    assigned_to: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    assigned_team: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    # Priority
    priority: Mapped[str] = mapped_column(
        String(20),
        default="MEDIUM"
    )

    # Workflow Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="OPEN"
    )

    # Operator Notes
    remarks: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
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

    # Relationship
    incident = relationship(
        "Incident",
        back_populates="ticket"
    )