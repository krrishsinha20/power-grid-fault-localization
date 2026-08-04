from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.pole import Pole
from app.models.incident import Incident


class DeadSensorService:
    """
    Flags poles whose device has gone silent while the pole itself is
    still (as far as we last knew) energized -- the "modem died, power
    is fine" case from the data contract, not a real outage.

    IMPORTANT: this does NOT filter on Pole.active. `active` is set to
    False by NoiseInjector precisely to simulate "this device just
    went silent" -- requiring active == True here would make this
    query exclude the exact poles it's supposed to catch. The real
    precondition is "this pole has a device at all" (a pole with no
    device was never going to report, silence there is not new
    information) plus the last_seen_at timeout.
    """

    def __init__(self, db: Session):

        self.db = db

    def detect(
        self,
        timeout_seconds: int = 60
    ):

        threshold = datetime.utcnow() - timedelta(
            seconds=timeout_seconds
        )

        dead_poles = (

            self.db.query(Pole)

            .filter(

                Pole.last_device_id.isnot(None),

                Pole.energized == True,

                Pole.last_seen_at < threshold

            )

            .all()

        )

        results = []

        for pole in dead_poles:

            existing = (

                self.db.query(Incident)

                .filter(

                    Incident.end_pole == pole.pole_id,

                    Incident.fault_type == "SENSOR_FAILURE",

                    Incident.status.notin_(

                        ["VERIFIED", "CLOSED"]

                    )

                )

                .first()

            )

            if existing:

                continue

            results.append(

                {

                    "start_pole": pole.parent.pole_id if pole.parent else pole.pole_id,

                    "end_pole": pole.pole_id,

                    "affected_poles": 1,

                    "affected_pole_ids": [

                        pole.pole_id

                    ],

                    "confidence": 95,

                    "penalties": [],

                    "latitude": pole.latitude,

                    "longitude": pole.longitude,

                    "feeder_id": pole.transformer.feeder_id,

                    "transformer_id": pole.transformer.transformer_id,

                    "pincode": pole.pincode,

                    "fault_type": "SENSOR_FAILURE"

                }

            )

            # Mark as flagged so a repeated localization pass (before
            # this incident is verified/closed) doesn't need to
            # re-derive it -- the `existing` check above already
            # guards against duplicate incidents, this just keeps the
            # pole's own state consistent with "known problem, not
            # silently fine".
            pole.active = False

        return results