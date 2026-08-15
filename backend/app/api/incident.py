from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.services.incident_service import IncidentService
from app.services.ai_service import AIService

from app.schemas.incident_schema import IncidentResponse


router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"]
)


@router.get(
    "",
    response_model=list[IncidentResponse]
)
def get_all_incidents(
    db: Session = Depends(get_db)
):

    service = IncidentService(db)

    return service.list_all()


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse
)
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db)
):

    service = IncidentService(db)

    incident = service.get_by_id(
        incident_id
    )

    if incident is None:

        raise HTTPException(
            status_code=404,
            detail="Incident not found."
        )

    return incident


@router.patch(
    "/{incident_id}/status"
)
def update_incident_status(
    incident_id: str,
    status: str,
    db: Session = Depends(get_db)
):

    service = IncidentService(db)

    incident = service.update_status(
        incident_id,
        status
    )

    if incident is None:

        raise HTTPException(
            status_code=404,
            detail="Incident not found."
        )

    db.commit()

    return {
        "message": "Incident status updated successfully."
    }


@router.post(
    "/{incident_id}/explain",
    response_model=IncidentResponse
)
def explain_incident(
    incident_id: str,
    db: Session = Depends(get_db)
):
    """
    On-demand AI explanation for an incident. This is deliberately
    NOT called automatically on incident creation, so a slow or
    unavailable AI provider never blocks fault detection or
    ticketing, which stays fully deterministic and AI-free.
    """

    service = IncidentService(db)

    incident = service.get_by_id(
        incident_id
    )

    if incident is None:

        raise HTTPException(
            status_code=404,
            detail="Incident not found."
        )

    try:

        ai_service = AIService()

        result = ai_service.generate_summary(incident)

        incident.ai_summary = result["ai_summary"]
        incident.root_cause = result["root_cause"]
        incident.recommended_action = result["recommended_action"]

        db.commit()
        db.refresh(incident)

    except Exception as e:

        import traceback
        print("=== AI EXPLAIN ERROR ===")
        traceback.print_exc()
        print("========================")

        db.rollback()

        raise HTTPException(
            status_code=503,
            detail=(
                "AI explanation is currently unavailable. "
                f"The incident itself is unaffected. ({str(e)})"
            )
        )

    return incident