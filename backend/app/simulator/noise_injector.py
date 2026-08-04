from datetime import datetime

from sqlalchemy.orm import Session

from app.models.pole import Pole
from app.models.telemetry import Telemetry


class NoiseInjector:
    """
    Injects the "not a fault" noise cases the brief calls out
    explicitly: a device dying while power is fine, duplicate
    telemetry retries, and out-of-order delivery. These exist so the
    system's trustworthiness claims (no cry-wolf on dead sensors,
    correct dedup, correct ordering) can actually be demonstrated and
    tested end-to-end via the simulator, not just asserted.
    """

    def __init__(self, db: Session):
        self.db = db

    def simulate_dead_sensor(self, pole_id: str):
        """
        Pole stays energized (power is fine) but its device goes
        silent -- no more telemetry, ever, until "repaired". We model
        this by pushing `last_seen_at` far enough into the past that
        DeadSensorService's timeout check fires on the next
        localization pass, WITHOUT touching `energized` or writing a
        power_lost event, since a real dead modem never gets a chance
        to say anything.
        """

        pole = (
            self.db.query(Pole)
            .filter(Pole.pole_id == pole_id)
            .first()
        )

        if pole is None:
            raise ValueError(f"Pole '{pole_id}' not found.")

        # Power stays on -- only the modem goes quiet.
        pole.energized = True
        pole.active = False
        pole.last_seen_at = datetime(1970, 1, 1)

        self.db.commit()

        return pole

    def simulate_duplicate(self, pole_id: str, repeat: int = 3):
        """
        Re-sends the exact same (device_id, seq) packet `repeat`
        times, the way an at-least-once-delivery retry storm does.
        TelemetryService.ingest() must apply the state change exactly
        once and treat the rest as no-ops -- this method calls
        TelemetryService directly (not the injector's raw DB writes)
        precisely so the dedup path under test is the real one.
        """

        from app.schemas.telemetry_schema import TelemetryCreate
        from app.services.telemetry_service import TelemetryService

        pole = (
            self.db.query(Pole)
            .filter(Pole.pole_id == pole_id)
            .first()
        )

        if pole is None:
            raise ValueError(f"Pole '{pole_id}' not found.")

        device_id = pole.last_device_id or f"DEV-{pole.pole_id}"
        seq = (pole.last_applied_seq or 0) + 1

        service = TelemetryService(self.db)

        sent = 0

        for _ in range(repeat):

            payload = TelemetryCreate(
                device_id=device_id,
                pole_id=pole.pole_id,
                event="power_lost",
                energized=False,
                sequence_number=seq,
                timestamp=datetime.utcnow(),
            )

            service.ingest(payload)
            sent += 1

        self.db.commit()

        return {"sent": sent, "applied_seq": seq}

    def simulate_out_of_order(self, pole_id: str):
        """
        Sends a NEWER power_lost first, then an OLDER (already
        superseded) power_restored for the same device -- mimicking
        two packets racing each other with the earlier one arriving
        late. The late `power_restored` must not be allowed to flip
        the pole back to energized once a newer `power_lost` has
        already been applied.
        """

        from app.schemas.telemetry_schema import TelemetryCreate
        from app.services.telemetry_service import TelemetryService

        pole = (
            self.db.query(Pole)
            .filter(Pole.pole_id == pole_id)
            .first()
        )

        if pole is None:
            raise ValueError(f"Pole '{pole_id}' not found.")

        device_id = pole.last_device_id or f"DEV-{pole.pole_id}"
        base_seq = pole.last_applied_seq or 0

        service = TelemetryService(self.db)

        newer_payload = TelemetryCreate(
            device_id=device_id,
            pole_id=pole.pole_id,
            event="power_lost",
            energized=False,
            sequence_number=base_seq + 2,
            timestamp=datetime.utcnow(),
        )
        service.ingest(newer_payload)

        # This "older" packet has a lower seq than what we just
        # applied -- it arrived late, e.g. queued during a radio
        # dropout. Must be rejected as stale, not applied.
        older_payload = TelemetryCreate(
            device_id=device_id,
            pole_id=pole.pole_id,
            event="power_restored",
            energized=True,
            sequence_number=base_seq + 1,
            timestamp=datetime.utcnow(),
        )
        service.ingest(older_payload)

        self.db.commit()

        self.db.refresh(pole)

        return pole