from datetime import datetime

from sqlalchemy.orm import Session

from app.models.pole import Pole
from app.models.telemetry import Telemetry


class TelemetryGenerator:

    def __init__(self, db: Session):
        self.db = db

    def generate_heartbeat(self):
        poles = (
            self.db.query(Pole)
            .filter(Pole.last_device_id.isnot(None))
            .all()
        )

        telemetry_events = []

        for pole in poles:
            device_id = pole.last_device_id
            next_seq = (pole.last_applied_seq or 0) + 1

            telemetry_events.append(
                Telemetry(
                    pole_id=pole.id,
                    device_id=device_id,
                    event="heartbeat",
                    energized=pole.energized,
                    sequence_number=next_seq,
                    timestamp=datetime.utcnow()
                )
            )

            pole.last_seen_at = datetime.utcnow()
            pole.last_applied_seq = next_seq

        return telemetry_events

    def save(self, telemetry_events):
        self.db.add_all(telemetry_events)
        self.db.flush()