from app.localization.graph_builder import GraphBuilder
from app.localization.boundary_detector import BoundaryDetector
from app.localization.downstream_counter import DownstreamCounter
from app.localization.confidence import ConfidenceEngine

from tests.conftest import make_transformer, make_line, make_pole


def _graph_for(db):
    return GraphBuilder(db).build()


class TestSpanFault:
    """
    A single snapped wire mid-line: everything upstream stays live,
    everything downstream goes dark. Localization must report exactly
    one boundary, on the correct span, with the correct downstream
    count -- not one alert per dark pole.
    """

    def test_detects_single_span_boundary(self, db):

        transformer = make_transformer(db)

        poles = make_line(
            db,
            transformer,
            ["P1", "P2", "P3", "P4", "P5"],
        )

        # Fault between P2 and P3: P1, P2 stay live; P3, P4, P5 go dark.
        poles[2].energized = False
        poles[3].energized = False
        poles[4].energized = False
        db.flush()

        graph = _graph_for(db)

        boundaries = BoundaryDetector(graph).detect()

        assert len(boundaries) == 1
        assert boundaries[0]["parent"] == "P2"
        assert boundaries[0]["child"] == "P3"

    def test_downstream_count_matches_dark_poles_only(self, db):

        transformer = make_transformer(db)

        poles = make_line(
            db,
            transformer,
            ["P1", "P2", "P3", "P4", "P5"],
        )

        poles[2].energized = False
        poles[3].energized = False
        poles[4].energized = False
        db.flush()

        graph = _graph_for(db)

        result = DownstreamCounter(graph).count("P3")

        assert result["count"] == 3
        assert set(result["poles"]) == {"P3", "P4", "P5"}
        assert result["reconnect_poles"] == []

    def test_does_not_merge_two_independent_faults_on_different_branches(
        self, db
    ):
        """
        Two spurs off the same transformer fail independently -- must
        produce two boundaries, not one merged incident and not
        thirty tiny ones.
        """

        transformer = make_transformer(db)

        root = make_pole(db, "P0", transformer, energized=True)

        branch_a = make_line(
            db, transformer, ["A1", "A2", "A3"], start_lat=18.5210
        )
        branch_a[0].parent_pole_id = root.id

        branch_b = make_line(
            db, transformer, ["B1", "B2", "B3"], start_lat=18.5300
        )
        branch_b[0].parent_pole_id = root.id

        db.flush()

        # Fault on branch A between A1 and A2
        branch_a[1].energized = False
        branch_a[2].energized = False

        # Fault on branch B between B1 and B2
        branch_b[1].energized = False
        branch_b[2].energized = False

        db.flush()

        graph = _graph_for(db)

        boundaries = BoundaryDetector(graph).detect()

        pairs = {(b["parent"], b["child"]) for b in boundaries}

        assert pairs == {("A1", "A2"), ("B1", "B2")}
        assert len(boundaries) == 2


class TestTransformerFault:

    def test_root_pole_dark_with_no_parent_is_transformer_fault(self, db):

        transformer = make_transformer(db)

        poles = make_line(db, transformer, ["P1", "P2", "P3"])

        for pole in poles:
            pole.energized = False

        db.flush()

        graph = _graph_for(db)

        boundaries = BoundaryDetector(graph).detect()

        assert len(boundaries) == 1
        assert boundaries[0]["parent"] is None
        assert boundaries[0]["child"] == "P1"


class TestSensorFailure:
    """
    The core "not a fault" case from 01-problem-context.md: a single
    pole reports dark but everything downstream of it is still live.
    This must not be counted as an outage propagating downstream --
    DownstreamCounter must stop at the first live descendant.
    """

    def test_dark_pole_with_live_children_does_not_count_them_as_affected(
        self, db
    ):

        transformer = make_transformer(db)

        poles = make_line(
            db,
            transformer,
            ["P1", "P2", "P3", "P4"],
        )

        # Only P2 is dark; P3, P4 (its descendants) are still live --
        # a lone dead/misreporting sensor, not a real fault.
        poles[1].energized = False
        db.flush()

        graph = _graph_for(db)

        result = DownstreamCounter(graph).count("P2")

        assert result["count"] == 1
        assert result["poles"] == ["P2"]
        assert result["reconnect_poles"] == ["P3"]

    def test_boundary_detector_still_flags_it_for_classification(self, db):
        """
        The boundary still gets reported (parent P1 live -> child P2
        dark) -- it's the affected-pole COUNT that must stay at 1 so
        downstream classification/confidence logic can recognize it
        as a sensor anomaly rather than a real outage.
        """

        transformer = make_transformer(db)

        poles = make_line(db, transformer, ["P1", "P2", "P3"])

        poles[1].energized = False
        db.flush()

        graph = _graph_for(db)

        boundaries = BoundaryDetector(graph).detect()

        assert len(boundaries) == 1
        assert boundaries[0]["parent"] == "P1"
        assert boundaries[0]["child"] == "P2"


class TestMissingDeviceBoundary:
    """
    A pole with no telemetry device sits on the fault boundary --
    localization must not pretend to know the exact span; it should
    walk past the undeviced pole(s) to the next pole with real
    telemetry and flag the result as uncertain.
    """

    def test_walks_past_undeviced_pole_to_find_confirmed_dark_pole(
        self, db
    ):

        transformer = make_transformer(db)

        poles = make_line(
            db,
            transformer,
            ["P1", "P2", "P3", "P4"],
        )

        # P2 has no device at all (state is meaningless/default).
        # P3 and P4 are genuinely dark and do have devices.
        poles[1].last_device_id = None
        poles[1].last_applied_seq = None
        poles[2].energized = False
        poles[3].energized = False
        db.flush()

        graph = _graph_for(db)

        boundaries = BoundaryDetector(graph).detect()

        assert len(boundaries) == 1
        boundary = boundaries[0]

        assert boundary["parent"] == "P1"
        assert boundary["child"] == "P3"
        assert boundary["boundary_uncertain"] is True
        assert "P2" in boundary["range_poles"]

    def test_confirmed_live_downstream_of_undeviced_pole_is_not_a_fault(
        self, db
    ):
        """
        If we walk past an undeviced pole and land on a pole that is
        actually LIVE, there is no fault on this branch at all --
        must not fabricate a boundary just because one pole in the
        middle has no reading.
        """

        transformer = make_transformer(db)

        poles = make_line(db, transformer, ["P1", "P2", "P3"])

        poles[1].last_device_id = None
        poles[1].last_applied_seq = None
        # P3 stays live.
        db.flush()

        graph = _graph_for(db)

        boundaries = BoundaryDetector(graph).detect()

        assert boundaries == []


class TestConfidence:

    def test_inferred_topology_lowers_confidence(self, db):

        transformer = make_transformer(db)
        make_line(db, transformer, ["P1", "P2"])

        graph = _graph_for(db)

        engine = ConfidenceEngine(graph)

        baseline = engine.calculate(affected_poles=5)
        degraded = engine.calculate(
            affected_poles=5, missing_topology=True
        )

        assert degraded["confidence"] < baseline["confidence"]

    def test_confidence_never_goes_below_zero(self, db):

        transformer = make_transformer(db)
        make_line(db, transformer, ["P1"])

        graph = _graph_for(db)

        engine = ConfidenceEngine(graph)

        result = engine.calculate(
            affected_poles=1,
            missing_telemetry=50,
            missing_topology=True,
            duplicate_events=50,
            inactive_devices=50,
        )

        assert result["confidence"] == 0.0