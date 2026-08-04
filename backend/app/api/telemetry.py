from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.schemas.telemetry_schema import (
    TelemetryCreate,
    TelemetryResponse
)

from app.models.incident import Incident

from app.services.telemetry_service import TelemetryService
from app.services.localization_service import LocalizationService
from app.services.classifier_service import ClassifierService
from app.services.incident_service import IncidentService
from app.services.ticket_service import TicketService
from app.services.dead_sensor_service import DeadSensorService
from app.services.verification_service import VerificationService


router = APIRouter(
    prefix="/telemetry",
    tags=["Telemetry"]
)


@router.post(
    "",
    response_model=TelemetryResponse
)
def ingest_telemetry(
    payload: TelemetryCreate,
    db: Session = Depends(get_db)
):

    try:

        telemetry_service = TelemetryService(db)

        telemetry = telemetry_service.ingest(
            payload
        )

        localization = LocalizationService(db)

        incidents = localization.process()

        dead_sensor_service = DeadSensorService(db)

        dead_sensor_incidents = dead_sensor_service.detect()

        incidents.extend(dead_sensor_incidents)

        if incidents:

            classifier = ClassifierService(db)

            incident_service = IncidentService(db)

            ticket_service = TicketService(db)

            for result in incidents:

                # Dead sensor incidents already know their type
                if "fault_type" in result:

                    fault_type = result["fault_type"]

                else:

                    fault_type = classifier.classify(
                        result
                    )

                incident = incident_service.create(

                    localization_result=result,

                    fault_type=fault_type,

                    feeder_id=result["feeder_id"],

                    transformer_id=result["transformer_id"],

                    latitude=result["latitude"],

                    longitude=result["longitude"],

                    pincode=result["pincode"]

                )

                ticket_service.create(
                    incident
                )

        # IMPORTANT: this is the real device path. `power_restored`
        # telemetry arrives here, not through the simulator's
        # /simulate/repair endpoint -- so restoration must be
        # re-checked on every ingest, not just when the simulator is
        # driving things. Without this, a real crew fixing a real
        # fault would never see the ticket auto-close, which breaks
        # the core "verified from telemetry, not a button" requirement.
        verification = VerificationService(db)

        open_incidents = (
            db.query(Incident)
            .filter(Incident.status.notin_(["VERIFIED", "CLOSED"]))
            .all()
        )

        for incident in open_incidents:

            ticket = incident.ticket

            if ticket is None:
                continue

            verification.verify(incident, ticket)

        db.commit()

        return telemetry

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )