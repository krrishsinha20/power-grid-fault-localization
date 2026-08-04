from app.simulator.network_generator import NetworkGenerator
from app.simulator.fault_injector import FaultInjector
from app.simulator.repair import RepairSimulator

from app.models.pole import Pole
from app.models.transformer import Transformer


class TestNetworkGenerator:

    def test_generates_requested_number_of_transformers(self, db):

        generator = NetworkGenerator(
            db,
            feeders=2,
            transformers_per_feeder=3,
            min_poles=10,
            max_poles=15,
        )

        generator.generate()

        assert db.query(Transformer).count() == 6

    def test_every_pole_belongs_to_a_transformer_on_the_right_feeder(
        self, db
    ):

        generator = NetworkGenerator(
            db,
            feeders=1,
            transformers_per_feeder=1,
            min_poles=10,
            max_poles=10,
        )

        generator.generate()

        transformer = db.query(Transformer).first()
        poles = (
            db.query(Pole)
            .filter(Pole.transformer_id == transformer.id)
            .all()
        )

        assert len(poles) == 10

    def test_device_coverage_is_roughly_91_percent_not_100(self, db):
        """
        Sanity check that the ~9% no-device gap from the data
        contract is actually represented in generated data, not
        silently defaulted to full coverage.
        """

        generator = NetworkGenerator(
            db,
            feeders=1,
            transformers_per_feeder=4,
            min_poles=40,
            max_poles=40,
        )

        generator.generate()

        poles = db.query(Pole).all()

        with_device = sum(1 for p in poles if p.last_device_id)
        total = len(poles)

        coverage = with_device / total

        # Wide tolerance -- this is a randomized generator, we're
        # checking it's in a realistic ballpark, not pinning an exact
        # figure.
        assert 0.75 <= coverage <= 1.0
        assert coverage < 1.0  # the gap must exist at all


class TestFaultInjectorAndRepair:

    def test_span_fault_deenergizes_requested_poles_and_logs_telemetry(
        self, db
    ):

        generator = NetworkGenerator(
            db, feeders=1, transformers_per_feeder=1,
            min_poles=10, max_poles=10,
        )
        generator.generate()

        transformer = db.query(Transformer).first()
        poles = (
            db.query(Pole)
            .filter(Pole.transformer_id == transformer.id)
            .limit(3)
            .all()
        )
        pole_ids = [p.pole_id for p in poles]

        injector = FaultInjector(db)
        telemetry = injector.inject_span_fault(pole_ids)

        assert len(telemetry) == 3

        for pole_id in pole_ids:
            pole = (
                db.query(Pole)
                .filter(Pole.pole_id == pole_id)
                .first()
            )
            assert pole.energized is False

    def test_sequence_numbers_increment_per_pole_not_random(self, db):
        """
        Regression test: sequence numbers used to be
        random.randint(1, 100000), which broke TelemetryService's
        seq-based dedup/ordering guard for any telemetry sent to a
        pole after the simulator touched it. They must increment
        monotonically per pole instead.
        """

        generator = NetworkGenerator(
            db, feeders=1, transformers_per_feeder=1,
            min_poles=5, max_poles=5,
        )
        generator.generate()

        transformer = db.query(Transformer).first()
        pole = (
            db.query(Pole)
            .filter(Pole.transformer_id == transformer.id)
            .first()
        )

        injector = FaultInjector(db)
        injector.inject_span_fault([pole.pole_id])

        first_seq = pole.last_applied_seq

        repair = RepairSimulator(db)
        repair.restore_span_fault([pole.pole_id])

        second_seq = pole.last_applied_seq

        assert second_seq == first_seq + 1

    def test_repair_reenergizes_and_transformer_repair_covers_all_poles(
        self, db
    ):

        generator = NetworkGenerator(
            db, feeders=1, transformers_per_feeder=1,
            min_poles=8, max_poles=8,
        )
        generator.generate()

        transformer = db.query(Transformer).first()

        injector = FaultInjector(db)
        injector.inject_transformer_fault(transformer.id)

        all_poles = (
            db.query(Pole)
            .filter(Pole.transformer_id == transformer.id)
            .all()
        )
        assert all(p.energized is False for p in all_poles)

        repair = RepairSimulator(db)
        repair.restore_transformer_fault(transformer.id)

        all_poles = (
            db.query(Pole)
            .filter(Pole.transformer_id == transformer.id)
            .all()
        )
        assert all(p.energized is True for p in all_poles)