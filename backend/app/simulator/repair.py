from datetime import datetime

from sqlalchemy.orm import Session

from app.models.pole import Pole
from app.models.transformer import Transformer
from app.models.telemetry import Telemetry


class RepairSimulator:
    """
    Same bookkeeping requirement as FaultInjector: sequence numbers
    must keep incrementing per pole (not random) and last_device_id /
    last_applied_seq must stay in sync, since real telemetry ingest
    for these poles later trusts that state for dedup/ordering.
    """

    def __init__(self, db: Session):
        self.db = db

    def restore_span_fault(self, pole_ids: list[str]):

        telemetry_events = []

        for pole_id in pole_ids:

            pole = (
                self.db.query(Pole)
                .filter(Pole.pole_id == pole_id)
                .first()
            )

            if pole is None:
                continue

            telemetry_events.append(
                self._apply_restore(pole)
            )

        self.db.add_all(telemetry_events)

        self.db.commit()

        return telemetry_events

    def restore_transformer_fault(self, transformer_id: int):

        poles = (
            self.db.query(Pole)
            .filter(Pole.transformer_id == transformer_id)
            .all()
        )

        pole_ids = [pole.pole_id for pole in poles]

        return self.restore_span_fault(pole_ids)

    def restore_feeder_fault(self, feeder_id: str):

        transformer_ids = [
            row.id
            for row in (
                self.db.query(Transformer)
                .filter(Transformer.feeder_id == feeder_id)
                .all()
            )
        ]

        poles = (
            self.db.query(Pole)
            .filter(Pole.transformer_id.in_(transformer_ids))
            .all()
        )

        pole_ids = [pole.pole_id for pole in poles]

        return self.restore_span_fault(pole_ids)

    def restore_all(self):

        poles = self.db.query(Pole).all()

        telemetry_events = []

        for pole in poles:
            telemetry_events.append(
                self._apply_restore(pole)
            )

        self.db.add_all(telemetry_events)

        self.db.commit()

        return telemetry_events

    def _apply_restore(self, pole: Pole) -> Telemetry:

        log_device_id = pole.last_device_id or f"DEV-{pole.pole_id}"

        next_seq = (pole.last_applied_seq or 0) + 1

        pole.energized = True
        pole.last_seen_at = datetime.utcnow()

        if pole.last_device_id is not None:
            pole.last_device_id = log_device_id
            pole.last_applied_seq = next_seq

        return Telemetry(

        pole_id=pole.id,

        device_id=log_device_id,

        event="power_restored",

        energized=True,

        sequence_number=next_seq,

        timestamp=datetime.utcnow()

    )