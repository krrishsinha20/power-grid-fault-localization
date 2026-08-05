from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.schemas.simulator_schema import (
    SpanFaultRequest,
    TransformerFaultRequest,
    FeederFaultRequest,
    SensorFaultRequest,
    DuplicateTelemetryRequest,
    OutOfOrderTelemetryRequest,
    RepairRequest,
    SimulationResponse
)

from app.models.transformer import Transformer
from app.models.pole import Pole
from app.models.telemetry import Telemetry
from app.models.incident import Incident
from app.models.ticket import Ticket

from app.simulator.network_generator import NetworkGenerator
from app.simulator.fault_injector import FaultInjector
from app.simulator.repair import RepairSimulator
from app.simulator.noise_injector import NoiseInjector

from app.services.localization_service import LocalizationService
from app.services.classifier_service import ClassifierService
from app.services.incident_service import IncidentService
from app.services.ticket_service import TicketService
from app.services.verification_service import VerificationService
from app.services.dead_sensor_service import DeadSensorService


router = APIRouter(
    prefix="/simulate",
    tags=["Simulator"]
)


def _run_localization_pipeline(db: Session):
    """
    Runs the same detect -> classify -> incident -> ticket
    pipeline that /telemetry triggers on ingest. Simulator
    endpoints call this explicitly since they write telemetry
    directly instead of going through the ingest endpoint.
    """

    localization = LocalizationService(db)

    incidents_found = localization.process()
    suppressed_count = getattr(localization, "suppressed_count", 0)

    dead_sensor_service = DeadSensorService(db)

    incidents_found.extend(dead_sensor_service.detect())

    created_incidents = []

    if incidents_found:

        classifier = ClassifierService(db)
        incident_service = IncidentService(db)
        ticket_service = TicketService(db)

        for result in incidents_found:
            # Idempotency check: don't create duplicate incident if active incident already exists for this end_pole
            existing_incident = (
                db.query(Incident)
                .filter(
                    Incident.end_pole == result["end_pole"],
                    Incident.status.notin_(["VERIFIED", "CLOSED"])
                )
                .first()
            )
            if existing_incident:
                continue

            if result.get("fault_type"):
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
                pincode=result["pincode"]
            )

            ticket = ticket_service.create(incident)

            if ticket is not None:
                created_incidents.append(incident)

    return created_incidents, suppressed_count


def _run_verification_pipeline(db: Session):
    """
    Checks every open (non-verified, non-closed) incident to see
    if its affected poles are all energized again, and closes out
    the incident/ticket if so. Called after a repair simulation.
    """

    verification = VerificationService(db)

    open_incidents = (
        db.query(Incident)
        .filter(Incident.status.notin_(["VERIFIED", "CLOSED"]))
        .all()
    )

    verified_count = 0

    for incident in open_incidents:

        ticket = incident.ticket

        if ticket is None:
            continue

        if verification.verify(incident, ticket):
            verified_count += 1

    return verified_count


@router.post(
    "/network",
    response_model=SimulationResponse
)
def generate_network(
    reset: bool = False,
    db: Session = Depends(get_db)
):

    try:

        existing = db.query(Transformer).first()

        if existing and not reset:

            pole_count = db.query(Pole).count()
            transformer_count = db.query(Transformer).count()

            return SimulationResponse(
                success=True,
                message=(
                    f"Network already exists "
                    f"({transformer_count} transformers, {pole_count} poles). "
                    f"Pass ?reset=true to regenerate."
                )
            )

        if existing and reset:

            db.query(Ticket).delete()
            db.query(Incident).delete()
            db.query(Telemetry).delete()
            db.query(Pole).delete()
            db.query(Transformer).delete()
            db.commit()

        generator = NetworkGenerator(db)

        graph = generator.generate()

        db.commit()

        return SimulationResponse(
            success=True,
            message=f"Network generated successfully. Nodes: {len(graph)}"
        )

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post(
    "/span",
    response_model=SimulationResponse
)
def inject_span_fault(
    request: SpanFaultRequest,
    db: Session = Depends(get_db)
):

    try:

        injector = FaultInjector(db)

        injector.inject_span_fault(
            request.pole_ids
        )

        created_incidents, suppressed_count = _run_localization_pipeline(db)

        db.commit()

        msg = f"Span fault injected successfully. Incidents created: {len(created_incidents)}"
        if suppressed_count > 0:
            msg += f" ({suppressed_count} fault alert(s) suppressed by active scheduled outage)"

        return SimulationResponse(
            success=True,
            message=msg
        )

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post(
    "/transformer",
    response_model=SimulationResponse
)
def inject_transformer_fault(
    request: TransformerFaultRequest,
    db: Session = Depends(get_db)
):

    try:

        transformer = (
            db.query(Transformer)
            .filter(Transformer.transformer_id == request.transformer_id)
            .first()
        )

        if transformer is None:

            raise HTTPException(
                status_code=404,
                detail=f"Transformer {request.transformer_id} not found."
            )

        injector = FaultInjector(db)

        injector.inject_transformer_fault(
            transformer.id
        )

        created_incidents, suppressed_count = _run_localization_pipeline(db)

        db.commit()

        msg = f"Transformer fault injected successfully. Incidents created: {len(created_incidents)}"
        if suppressed_count > 0:
            msg += f" ({suppressed_count} fault alert(s) suppressed by active scheduled outage on {request.transformer_id})"

        return SimulationResponse(
            success=True,
            message=msg
        )

    except HTTPException:

        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post(
    "/feeder",
    response_model=SimulationResponse
)
def inject_feeder_fault(
    request: FeederFaultRequest,
    db: Session = Depends(get_db)
):
    """
    Takes every transformer on a feeder dark at once -- distinct from
    a transformer fault (one DT) and from a span fault (one branch).
    """

    try:

        transformers = (
            db.query(Transformer)
            .filter(Transformer.feeder_id == request.feeder_id)
            .all()
        )

        if not transformers:

            raise HTTPException(
                status_code=404,
                detail=f"Feeder {request.feeder_id} has no transformers."
            )

        injector = FaultInjector(db)

        injector.inject_feeder_fault(request.feeder_id)

        created_incidents, suppressed_count = _run_localization_pipeline(db)

        db.commit()

        msg = f"Feeder fault injected successfully. Incidents created: {len(created_incidents)}"
        if suppressed_count > 0:
            msg += f" ({suppressed_count} fault alert(s) suppressed by active scheduled outage on feeder {request.feeder_id})"

        return SimulationResponse(
            success=True,
            message=msg
        )

    except HTTPException:

        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post(
    "/noise/sensor-failure",
    response_model=SimulationResponse
)
def simulate_sensor_failure(
    request: SensorFaultRequest,
    db: Session = Depends(get_db)
):
    """
    Kills a device while the pole stays powered -- this must NOT
    produce a fault ticket. It should only ever surface (if at all)
    as a SENSOR_FAILURE incident once the heartbeat timeout elapses,
    never as an outage.
    """

    try:

        noise = NoiseInjector(db)

        noise.simulate_dead_sensor(request.pole_id)

        created_incidents, _ = _run_localization_pipeline(db)

        db.commit()

        return SimulationResponse(
            success=True,
            message=(
                f"Sensor failure simulated on {request.pole_id} "
                f"(power unaffected). "
                f"Incidents created: {len(created_incidents)}"
            )
        )

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post(
    "/noise/duplicate-telemetry",
    response_model=SimulationResponse
)
def simulate_duplicate_telemetry(
    request: DuplicateTelemetryRequest,
    db: Session = Depends(get_db)
):
    """
    Re-sends the same (device_id, seq) packet multiple times, the
    way an at-least-once delivery retry does. Should result in
    exactly one applied state change, not one incident per retry.
    """

    try:

        noise = NoiseInjector(db)

        result = noise.simulate_duplicate(
            request.pole_id,
            repeat=request.repeat_count
        )

        created_incidents, _ = _run_localization_pipeline(db)

        db.commit()

        return SimulationResponse(
            success=True,
            message=(
                f"Sent {result['sent']} duplicate packets for "
                f"{request.pole_id}. "
                f"Incidents created: {len(created_incidents)}"
            )
        )

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post(
    "/noise/out-of-order",
    response_model=SimulationResponse
)
def simulate_out_of_order_telemetry(
    request: OutOfOrderTelemetryRequest,
    db: Session = Depends(get_db)
):
    """
    Sends a newer power_lost, then an older (already-superseded)
    power_restored for the same device -- the late packet must not
    be allowed to flip the pole back to energized.
    """

    try:

        noise = NoiseInjector(db)

        noise.simulate_out_of_order(request.pole_id)

        created_incidents, _ = _run_localization_pipeline(db)

        db.commit()

        return SimulationResponse(
            success=True,
            message=(
                f"Out-of-order telemetry simulated for "
                f"{request.pole_id}. "
                f"Incidents created: {len(created_incidents)}"
            )
        )

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post(
    "/repair",
    response_model=SimulationResponse
)
def repair_fault(
    request: RepairRequest,
    db: Session = Depends(get_db)
):

    try:

        repair = RepairSimulator(db)

        repair.restore_span_fault(
            request.pole_ids
        )

        verified_count = _run_verification_pipeline(db)

        db.commit()

        return SimulationResponse(
            success=True,
            message=(
                f"Fault repaired successfully. "
                f"Incidents verified: {verified_count}"
            )
        )

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post(
    "/repair/feeder",
    response_model=SimulationResponse
)
def repair_feeder(
    request: FeederFaultRequest,
    db: Session = Depends(get_db)
):

    try:

        repair = RepairSimulator(db)

        repair.restore_feeder_fault(request.feeder_id)

        verified_count = _run_verification_pipeline(db)

        db.commit()

        return SimulationResponse(
            success=True,
            message=(
                f"Feeder repaired successfully. "
                f"Incidents verified: {verified_count}"
            )
        )

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )