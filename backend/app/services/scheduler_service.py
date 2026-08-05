import asyncio
import logging

from app.database.database import SessionLocal
from app.simulator.telemetry_generator import TelemetryGenerator
from app.services.dead_sensor_service import DeadSensorService
from app.services.localization_service import LocalizationService
from app.services.classifier_service import ClassifierService
from app.services.incident_service import IncidentService
from app.services.ticket_service import TicketService
from app.models.incident import Incident

logger = logging.getLogger("scheduler")

HEARTBEAT_INTERVAL_SECONDS = 300


async def heartbeat_loop():
    while True:
        try:
            _run_tick()
        except Exception:
            logger.exception("Heartbeat tick failed")
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


def _run_tick():
    db = SessionLocal()
    try:
        generator = TelemetryGenerator(db)
        events = generator.generate_heartbeat()
        generator.save(events)

        dead_sensor_service = DeadSensorService(db)
        dead_sensor_incidents = dead_sensor_service.detect()

        localization = LocalizationService(db)
        localization_incidents = localization.process()

        incidents_found = dead_sensor_incidents + localization_incidents

        if incidents_found:
            classifier = ClassifierService(db)
            incident_service = IncidentService(db)
            ticket_service = TicketService(db)

            for result in incidents_found:
                # Idempotency: don't create a duplicate incident if an active
                # one already exists for this end_pole (same guard as telemetry.py).
                existing = (
                    db.query(Incident)
                    .filter(
                        Incident.end_pole == result["end_pole"],
                        Incident.status.notin_(["VERIFIED", "CLOSED"])
                    )
                    .first()
                )
                if existing:
                    continue

                if "fault_type" in result and result["fault_type"]:
                    fault_type = result["fault_type"]
                else:
                    fault_type = classifier.classify(result)

                incident = incident_service.create(
                    localization_result=result,
                    fault_type=fault_type,
                    feeder_id=result["feeder_id"],
                    transformer_id=result["transformer_id"],
                    latitude=result["latitude"],
                    longitude=result["longitude"],
                    pincode=result["pincode"],
                )
                ticket_service.create(incident)

        db.commit()
    finally:
        db.close()