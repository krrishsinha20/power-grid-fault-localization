from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.models.scheduled_outage import ScheduledOutage

from app.schemas.scheduled_outage_schema import (
    ScheduledOutageCreate,
    ScheduledOutageUpdate,
    ScheduledOutageResponse
)


router = APIRouter(
    prefix="/scheduled-outages",
    tags=["Scheduled Outages"]
)


@router.get(
    "",
    response_model=list[ScheduledOutageResponse]
)
def list_scheduled_outages(
    db: Session = Depends(get_db)
):

    return (
        db.query(ScheduledOutage)
        .order_by(ScheduledOutage.start_time.desc())
        .all()
    )


@router.post(
    "",
    response_model=ScheduledOutageResponse
)
def create_scheduled_outage(
    payload: ScheduledOutageCreate,
    db: Session = Depends(get_db)
):

    existing = (
        db.query(ScheduledOutage)
        .filter(
            ScheduledOutage.outage_id == payload.outage_id
        )
        .first()
    )

    if existing:

        raise HTTPException(
            status_code=409,
            detail=f"Scheduled outage '{payload.outage_id}' already exists."
        )

    outage = ScheduledOutage(
        **payload.model_dump()
    )

    db.add(outage)
    db.commit()
    db.refresh(outage)

    return outage


@router.put(
    "/{outage_id}",
    response_model=ScheduledOutageResponse
)
def update_scheduled_outage(
    outage_id: str,
    payload: ScheduledOutageUpdate,
    db: Session = Depends(get_db)
):

    outage = (
        db.query(ScheduledOutage)
        .filter(
            ScheduledOutage.outage_id == outage_id
        )
        .first()
    )

    if outage is None:

        raise HTTPException(
            status_code=404,
            detail="Scheduled outage not found."
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(outage, key, value)

    db.commit()
    db.refresh(outage)

    return outage


@router.delete(
    "/{outage_id}"
)
def delete_scheduled_outage(
    outage_id: str,
    db: Session = Depends(get_db)
):

    outage = (
        db.query(ScheduledOutage)
        .filter(
            ScheduledOutage.outage_id == outage_id
        )
        .first()
    )

    if outage is None:

        raise HTTPException(
            status_code=404,
            detail="Scheduled outage not found."
        )

    db.delete(outage)
    db.commit()

    return {
        "success": True,
        "message": f"Scheduled outage '{outage_id}' deleted successfully."
    }