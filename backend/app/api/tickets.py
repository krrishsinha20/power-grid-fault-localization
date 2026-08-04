from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.services.ticket_service import TicketService

from app.schemas.ticket_schema import TicketResponse


router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"]
)


@router.get(
    "",
    response_model=list[TicketResponse]
)
def get_all_tickets(
    db: Session = Depends(get_db)
):

    service = TicketService(db)

    return service.list_all()


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse
)
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db)
):

    service = TicketService(db)

    ticket = service.get_by_ticket_id(
        ticket_id
    )

    if ticket is None:

        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    return ticket


@router.patch(
    "/{ticket_id}/status"
)
def update_status(
    ticket_id: str,
    status: str,
    db: Session = Depends(get_db)
):

    service = TicketService(db)

    ticket = service.update_status(
        ticket_id,
        status
    )

    if ticket is None:

        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    db.commit()

    return {

        "message": "Ticket updated successfully."

    }


@router.post(
    "/{ticket_id}/close"
)
def close_ticket(
    ticket_id: str,
    db: Session = Depends(get_db)
):

    service = TicketService(db)

    ticket = service.close(
        ticket_id
    )

    if ticket is None:

        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    db.commit()

    return {

        "message": "Ticket closed successfully."

    }