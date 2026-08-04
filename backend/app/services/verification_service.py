from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.ticket import Ticket
from app.models.pole import Pole


class VerificationService:

    def __init__(self, db: Session):
        self.db = db

    def verify(
        self,
        incident: Incident,
        ticket: Ticket
    ) -> bool:

        """
        Verify whether all affected poles
        are energized again.
        """

        affected_poles = incident.affected_pole_ids

        for pole_id in affected_poles:

            pole = (
                self.db.query(Pole)
                .filter(Pole.pole_id == pole_id)
                .first()
            )

            if pole is None:
                return False

            if not pole.energized:
                return False

        incident.status = "VERIFIED"

        ticket.status = "CLOSED"

        ticket.remarks = "Fault repaired and verified successfully."

        self.db.flush()

        self.db.refresh(incident)
        self.db.refresh(ticket)

        return True

    def rollback(
        self,
        incident: Incident,
        ticket: Ticket
    ):

        """
        Verification failed.
        Re-open the ticket.
        """

        incident.status = "DETECTED"

        ticket.status = "OPEN"

        ticket.remarks = "Verification failed."

        self.db.flush()

        self.db.refresh(incident)
        self.db.refresh(ticket)

        return False