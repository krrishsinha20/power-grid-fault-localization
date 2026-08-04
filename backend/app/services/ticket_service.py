import uuid

from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.incident import Incident


class TicketService:

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        incident: Incident,
        priority: str = "HIGH"
    ) -> Ticket:

        existing = (
            self.db.query(Ticket)
            .filter(Ticket.incident_id == incident.id)
            .first()
        )

        if existing:
            return existing

        ticket = Ticket(

            ticket_id=f"TKT-{uuid.uuid4().hex[:8].upper()}",

            incident_id=incident.id,

            priority=priority,

            status="OPEN"

        )

        self.db.add(ticket)

        self.db.flush()

        self.db.refresh(ticket)

        return ticket

    def assign(
        self,
        ticket_id: str,
        engineer: str,
        team: str
    ) -> Ticket | None:

        ticket = self.get_by_ticket_id(ticket_id)

        if ticket is None:
            return None

        ticket.assigned_to = engineer
        ticket.assigned_team = team
        ticket.status = "ASSIGNED"

        self.db.flush()
        self.db.refresh(ticket)

        return ticket

    def update_status(
        self,
        ticket_id: str,
        status: str
    ) -> Ticket | None:

        ticket = self.get_by_ticket_id(ticket_id)

        if ticket is None:
            return None

        ticket.status = status

        self.db.flush()
        self.db.refresh(ticket)

        return ticket

    def close(
        self,
        ticket_id: str,
        remarks: str = "Fault resolved successfully."
    ) -> Ticket | None:

        ticket = self.get_by_ticket_id(ticket_id)

        if ticket is None:
            return None

        ticket.status = "CLOSED"
        ticket.remarks = remarks

        self.db.flush()
        self.db.refresh(ticket)

        return ticket

    def get_by_ticket_id(
        self,
        ticket_id: str
    ) -> Ticket | None:

        return (

            self.db.query(Ticket)

            .filter(
                Ticket.ticket_id == ticket_id
            )

            .first()

        )

    def list_all(self):

        return (

            self.db.query(Ticket)

            .order_by(
                Ticket.created_at.desc()
            )

            .all()

        )