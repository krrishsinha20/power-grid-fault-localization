from sqlalchemy.orm import Session

from app.models.pole import Pole
from app.models.transformer import Transformer


class ClassifierService:

    def __init__(self, db: Session):
        self.db = db

    def classify(
        self,
        localization_result: dict
    ) -> str:

        affected = localization_result["affected_poles"]

        start = localization_result["start_pole"]

        end = localization_result["end_pole"]

        # ---------------------------------
        # Sensor Failure
        # ---------------------------------
        if localization_result.get("fault_type") == "SENSOR_FAILURE":
            return "SENSOR_FAILURE"

        # ---------------------------------
        # Feeder Fault
        # Checked feeder-scoped, not network-wide: every transformer
        # under this incident's feeder must have zero energized
        # poles. A single dark feeder must not require every OTHER
        # feeder in the subdivision to also be dark before it
        # qualifies -- that was the old (wrong) check.
        # ---------------------------------
        feeder_id = localization_result.get("feeder_id")

        if feeder_id and feeder_id != "UNKNOWN":

            transformer_ids = [
                row.id
                for row in (
                    self.db.query(Transformer)
                    .filter(Transformer.feeder_id == feeder_id)
                    .all()
                )
            ]

            if transformer_ids:

                feeder_total = (
                    self.db.query(Pole)
                    .filter(Pole.transformer_id.in_(transformer_ids))
                    .count()
                )

                feeder_energized = (
                    self.db.query(Pole)
                    .filter(
                        Pole.transformer_id.in_(transformer_ids),
                        Pole.energized == True
                    )
                    .count()
                )

                if feeder_total > 0 and feeder_energized == 0:
                    return "FEEDER_FAULT"

        # ---------------------------------
        # Transformer Fault
        # Root pole has no parent
        # ---------------------------------
        if start is None and end is not None:
            return "TRANSFORMER_FAULT"

        # ---------------------------------
        # Span Fault
        # ---------------------------------
        if start is not None and end is not None:
            return "SPAN_FAULT"

        return "UNKNOWN"

    def determine_priority(
        self,
        fault_type: str,
        affected_poles: int
    ) -> str:

        if fault_type == "FEEDER_FAULT":
            return "CRITICAL"

        if fault_type == "TRANSFORMER_FAULT":
            return "CRITICAL"

        if affected_poles >= 50:
            return "CRITICAL"

        if affected_poles >= 20:
            return "HIGH"

        if affected_poles >= 5:
            return "MEDIUM"

        return "LOW"