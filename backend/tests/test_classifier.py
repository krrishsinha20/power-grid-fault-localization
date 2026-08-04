from app.services.classifier_service import ClassifierService

from tests.conftest import make_transformer, make_line


class TestClassifierFaultType:

    def test_span_fault_when_boundary_has_both_start_and_end(self, db):

        transformer = make_transformer(db)
        make_line(db, transformer, ["P1", "P2", "P3"])

        classifier = ClassifierService(db)

        result = classifier.classify({
            "start_pole": "P1",
            "end_pole": "P2",
            "affected_poles": 2,
            "fault_type": None,
        })

        assert result == "SPAN_FAULT"

    def test_transformer_fault_when_no_start_pole(self, db):

        transformer = make_transformer(db)
        poles = make_line(db, transformer, ["P1", "P2", "P3"])

        for pole in poles:
            pole.energized = False
        db.flush()

        classifier = ClassifierService(db)

        result = classifier.classify({
            "start_pole": None,
            "end_pole": "P1",
            "affected_poles": 3,
            "fault_type": None,
        })

        assert result == "TRANSFORMER_FAULT"

    def test_feeder_fault_when_entire_network_is_dark(self, db):
        """
        If every pole in the network is de-energized, this looks like
        a feeder-wide (or larger) event rather than a single span or
        transformer -- classifier should escalate regardless of what
        the localization boundary itself reported.
        """

        transformer = make_transformer(db)
        poles = make_line(db, transformer, ["P1", "P2"])

        for pole in poles:
            pole.energized = False
        db.flush()

        classifier = ClassifierService(db)

        result = classifier.classify({
            "start_pole": "P1",
            "end_pole": "P2",
            "affected_poles": 2,
            "fault_type": None,
        })

        assert result == "FEEDER_FAULT"

    def test_sensor_failure_passed_through_when_already_flagged(self, db):

        transformer = make_transformer(db)
        make_line(db, transformer, ["P1", "P2", "P3"])

        classifier = ClassifierService(db)

        result = classifier.classify({
            "start_pole": "P1",
            "end_pole": "P2",
            "affected_poles": 1,
            "fault_type": "SENSOR_FAILURE",
        })

        assert result == "SENSOR_FAILURE"


class TestClassifierPriority:

    def test_transformer_and_feeder_faults_are_always_critical(self, db):

        classifier = ClassifierService(db)

        assert classifier.determine_priority(
            "TRANSFORMER_FAULT", affected_poles=1
        ) == "CRITICAL"

        assert classifier.determine_priority(
            "FEEDER_FAULT", affected_poles=1
        ) == "CRITICAL"

    def test_span_fault_priority_scales_with_affected_poles(self, db):

        classifier = ClassifierService(db)

        assert classifier.determine_priority(
            "SPAN_FAULT", affected_poles=2
        ) == "LOW"

        assert classifier.determine_priority(
            "SPAN_FAULT", affected_poles=10
        ) == "MEDIUM"

        assert classifier.determine_priority(
            "SPAN_FAULT", affected_poles=25
        ) == "HIGH"

        assert classifier.determine_priority(
            "SPAN_FAULT", affected_poles=60
        ) == "CRITICAL"