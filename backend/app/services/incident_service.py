import uuid

from sqlalchemy.orm import Session

from app.models.incident import Incident


class IncidentService:

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        localization_result: dict,
        fault_type: str,
        feeder_id: str,
        transformer_id: str,
        latitude: float,
        longitude: float,
        pincode: str,
    ) -> Incident:

        incident = Incident(

            incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",

            fault_type=fault_type,

            feeder_id=feeder_id,

            transformer_id=transformer_id,

            start_pole=localization_result["start_pole"],

            end_pole=localization_result["end_pole"],

            affected_pole_count=localization_result[
                "affected_poles"
            ],

            affected_pole_ids=localization_result[
                "affected_pole_ids"
            ],

            confidence=localization_result[
                "confidence"
            ],

            latitude=latitude,

            longitude=longitude,

            pincode=pincode,

            status="DETECTED"

        )

        self.db.add(incident)

        self.db.flush()

        self.db.refresh(incident)

        return incident

    def get_by_id(
        self,
        incident_id: str
    ):

        return (

            self.db.query(Incident)

            .filter(
                Incident.incident_id == incident_id
            )

            .first()

        )

    def list_all(self):

        return (

            self.db.query(Incident)

            .order_by(
                Incident.created_at.desc()
            )

            .all()

        )

    def update_status(
        self,
        incident_id: str,
        status: str
    ):

        incident = self.get_by_id(
            incident_id
        )

        if incident is None:

            return None

        incident.status = status

        self.db.flush()

        self.db.refresh(incident)

        return incident