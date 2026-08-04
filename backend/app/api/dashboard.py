from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.models.incident import Incident
from app.models.ticket import Ticket
from app.models.pole import Pole


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("")
def dashboard(
    db: Session = Depends(get_db)
):

    total_poles = db.query(Pole).count()

    healthy_poles = (
        db.query(Pole)
        .filter(Pole.energized == True)
        .count()
    )

    faulty_poles = total_poles - healthy_poles

    active_incidents = (
        db.query(Incident)
        .filter(
            Incident.status.in_(
                [
                    "DETECTED",
                    "ASSIGNED",
                    "IN_PROGRESS"
                ]
            )
        )
        .count()
    )

    open_tickets = (
        db.query(Ticket)
        .filter(Ticket.status != "CLOSED")
        .count()
    )

    return {
        "total_poles": total_poles,
        "healthy_poles": healthy_poles,
        "faulty_poles": faulty_poles,
        "active_incidents": active_incidents,
        "open_tickets": open_tickets
    }