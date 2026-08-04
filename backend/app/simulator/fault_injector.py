from datetime import datetime

from sqlalchemy.orm import Session

from app.models.pole import Pole
from app.models.transformer import Transformer
from app.models.telemetry import Telemetry


class FaultInjector:
    """
    Writes directly to pole state + telemetry log, bypassing the
    `/telemetry` ingest endpoint (the simulator is standing in for
    real devices, not for the endpoint itself).
    """

    def __init__(self, db: Session):
        self.db = db

    def inject_span_fault(self, pole_ids: list[str]):
        from app.localization.graph_builder import GraphBuilder
        import networkx as nx

        graph = GraphBuilder(self.db).build()

        all_affected = set(pole_ids)
        for pid in pole_ids:
            if pid in graph:
                all_affected.update(nx.descendants(graph, pid))

        poles = (
            self.db.query(Pole)
            .filter(Pole.pole_id.in_(all_affected))
            .all()
        )

        now = datetime.utcnow()
        telemetry = []

        for pole in poles:
            telemetry.append(
                self._apply(
                    pole=pole,
                    energized=False,
                    event="power_lost",
                    now=now,
                )
            )

        self.db.add_all(telemetry)
        self.db.commit()

        return telemetry

    def inject_transformer_fault(self, transformer_id: int):

        poles = (
            self.db.query(Pole)
            .filter(Pole.transformer_id == transformer_id)
            .all()
        )

        now = datetime.utcnow()
        telemetry = []

        for pole in poles:
            telemetry.append(
                self._apply(
                    pole=pole,
                    energized=False,
                    event="power_lost",
                    now=now,
                )
            )

        self.db.add_all(telemetry)
        self.db.commit()

        return telemetry

    def inject_feeder_fault(self, feeder_id: str):

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

        now = datetime.utcnow()
        telemetry = []

        for pole in poles:
            telemetry.append(
                self._apply(
                    pole=pole,
                    energized=False,
                    event="power_lost",
                    now=now,
                )
            )

        self.db.add_all(telemetry)
        self.db.commit()

        return telemetry

    def restore(self, pole_ids: list[str]):

        poles = (
            self.db.query(Pole)
            .filter(Pole.pole_id.in_(pole_ids))
            .all()
        )

        now = datetime.utcnow()
        telemetry = []

        for pole in poles:
            telemetry.append(
                self._apply(
                    pole=pole,
                    energized=True,
                    event="power_restored",
                    now=now,
                )
            )

        self.db.add_all(telemetry)
        self.db.commit()

        return telemetry

    def _apply(
        self,
        pole: Pole,
        energized: bool,
        event: str,
        now: datetime,
    ) -> Telemetry:

        log_device_id = pole.last_device_id or f"DEV-{pole.pole_id}"

        next_seq = (pole.last_applied_seq or 0) + 1

        pole.energized = energized
        pole.last_seen_at = now

        if pole.last_device_id is not None:
            pole.last_device_id = log_device_id
            pole.last_applied_seq = next_seq

        return Telemetry(
            pole_id=pole.id,
            device_id=log_device_id,
            event=event,
            energized=energized,
            sequence_number=next_seq,
            timestamp=now,
        )