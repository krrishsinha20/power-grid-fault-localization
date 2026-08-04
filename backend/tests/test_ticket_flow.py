from app.services.incident_service import IncidentService
from app.services.ticket_service import TicketService
from app.services.verification_service import VerificationService

from tests.conftest import make_transformer, make_line


def _sample_localization_result(poles):

    return {
        "start_pole": poles[0].pole_id,
        "end_pole": poles[1].pole_id,
        "affected_poles": len(poles) - 1,
        "affected_pole_ids": [p.pole_id for p in poles[1:]],
        "confidence": 90.0,
        "penalties": [],
    }


class TestIncidentTicketCreation:

    def test_creating_incident_also_needs_explicit_ticket_creation(self, db):

        transformer = make_transformer(db)
        poles = make_line(db, transformer, ["P1", "P2", "P3"])

        for pole in poles[1:]:
            pole.energized = False
        db.flush()

        incident_service = IncidentService(db)

        incident = incident_service.create(
            localization_result=_sample_localization_result(poles),
            fault_type="SPAN_FAULT",
            feeder_id=transformer.feeder_id,
            transformer_id=transformer.transformer_id,
            latitude=poles[1].latitude,
            longitude=poles[1].longitude,
            pincode=poles[1].pincode,
        )

        assert incident.status == "DETECTED"
        assert incident.affected_pole_count == 2

        ticket_service = TicketService(db)

        ticket = ticket_service.create(incident)

        assert ticket.status == "OPEN"
        assert ticket.incident_id == incident.id


class TestTicketLifecycle:

    def _make_incident_and_ticket(self, db):

        transformer = make_transformer(db)
        poles = make_line(db, transformer, ["P1", "P2", "P3"])

        for pole in poles[1:]:
            pole.energized = False
        db.flush()

        incident_service = IncidentService(db)
        ticket_service = TicketService(db)

        incident = incident_service.create(
            localization_result=_sample_localization_result(poles),
            fault_type="SPAN_FAULT",
            feeder_id=transformer.feeder_id,
            transformer_id=transformer.transformer_id,
            latitude=poles[1].latitude,
            longitude=poles[1].longitude,
            pincode=poles[1].pincode,
        )

        ticket = ticket_service.create(incident)

        return poles, incident, ticket, ticket_service

    def test_assign_moves_ticket_to_assigned(self, db):

        _, _, ticket, ticket_service = self._make_incident_and_ticket(db)

        updated = ticket_service.assign(
            ticket.ticket_id, engineer="Ravi", team="Line Crew A"
        )

        assert updated.status == "ASSIGNED"
        assert updated.assigned_to == "Ravi"

    def test_manual_close_without_telemetry_is_not_the_verified_path(
        self, db
    ):
        """
        TicketService.close() is a raw status setter used for manual
        admin overrides -- it must NOT be what the "resolved by crew"
        button in the UI calls, because it does not check telemetry
        at all. The UI's resolve action must go through
        VerificationService instead. This test documents that
        close() alone proves nothing about the poles' real state.
        """

        poles, incident, ticket, ticket_service = (
            self._make_incident_and_ticket(db)
        )

        # Poles are still dark in reality.
        assert poles[1].energized is False

        closed = ticket_service.close(ticket.ticket_id)

        # close() happily marks it closed regardless of telemetry --
        # this is exactly why the operator-facing "mark resolved"
        # action must call VerificationService.verify(), not this.
        assert closed.status == "CLOSED"


class TestVerification:

    def test_verify_fails_while_poles_still_dark(self, db):

        transformer = make_transformer(db)
        poles = make_line(db, transformer, ["P1", "P2", "P3"])

        for pole in poles[1:]:
            pole.energized = False
        db.flush()

        incident_service = IncidentService(db)
        ticket_service = TicketService(db)
        verification = VerificationService(db)

        incident = incident_service.create(
            localization_result=_sample_localization_result(poles),
            fault_type="SPAN_FAULT",
            feeder_id=transformer.feeder_id,
            transformer_id=transformer.transformer_id,
            latitude=poles[1].latitude,
            longitude=poles[1].longitude,
            pincode=poles[1].pincode,
        )
        ticket = ticket_service.create(incident)

        result = verification.verify(incident, ticket)

        assert result is False
        assert incident.status == "DETECTED"
        assert ticket.status == "OPEN"

    def test_verify_succeeds_once_all_affected_poles_are_live_again(
        self, db
    ):

        transformer = make_transformer(db)
        poles = make_line(db, transformer, ["P1", "P2", "P3"])

        for pole in poles[1:]:
            pole.energized = False
        db.flush()

        incident_service = IncidentService(db)
        ticket_service = TicketService(db)
        verification = VerificationService(db)

        incident = incident_service.create(
            localization_result=_sample_localization_result(poles),
            fault_type="SPAN_FAULT",
            feeder_id=transformer.feeder_id,
            transformer_id=transformer.transformer_id,
            latitude=poles[1].latitude,
            longitude=poles[1].longitude,
            pincode=poles[1].pincode,
        )
        ticket = ticket_service.create(incident)

        # Crew fixes it -- telemetry reports poles live again.
        for pole in poles[1:]:
            pole.energized = True
        db.flush()

        result = verification.verify(incident, ticket)

        assert result is True
        assert incident.status == "VERIFIED"
        assert ticket.status == "CLOSED"

    def test_rollback_reopens_incident_and_ticket(self, db):

        transformer = make_transformer(db)
        poles = make_line(db, transformer, ["P1", "P2", "P3"])

        for pole in poles[1:]:
            pole.energized = False
        db.flush()

        incident_service = IncidentService(db)
        ticket_service = TicketService(db)
        verification = VerificationService(db)

        incident = incident_service.create(
            localization_result=_sample_localization_result(poles),
            fault_type="SPAN_FAULT",
            feeder_id=transformer.feeder_id,
            transformer_id=transformer.transformer_id,
            latitude=poles[1].latitude,
            longitude=poles[1].longitude,
            pincode=poles[1].pincode,
        )
        ticket = ticket_service.create(incident)

        verification.rollback(incident, ticket)

        assert incident.status == "DETECTED"
        assert ticket.status == "OPEN"
        assert ticket.remarks == "Verification failed."