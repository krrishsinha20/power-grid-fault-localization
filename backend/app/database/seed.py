from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.pole import Pole
from app.models.scheduled_outage import ScheduledOutage
from app.simulator.network_generator import NetworkGenerator


def seed_database(db: Session):

    print("Seeding database...")

    existing_poles = db.query(Pole).first()

    if existing_poles:
        print("Database already has data. Skipping seed.")
        return

    # --- Network (transformers + poles) ---
    generator = NetworkGenerator(
        db=db,
        feeders=3,
        transformers_per_feeder=5,
        min_poles=20,
        max_poles=40,
    )
    graph = generator.generate()
    print(f"Seeded network: {len(graph)} poles across "
          f"{generator.feeders * generator.transformers_per_feeder} transformers.")

    # --- Scheduled outages ---
    now = datetime.utcnow()

    scheduled_outages = [
        ScheduledOutage(
            outage_id="SO-SEED-001",
            feeder_id="F001",
            transformer_id=None,
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=4),
            reason="Planned maintenance - jumper replacement",
            status="ACTIVE",
        ),
        ScheduledOutage(
            outage_id="SO-SEED-002",
            feeder_id="F002",
            transformer_id="DT0006",
            start_time=now + timedelta(hours=6),
            end_time=now + timedelta(hours=7),
            reason="Load shedding",
            status="ACTIVE",
        ),
    ]

    db.add_all(scheduled_outages)
    db.commit()

    print(f"Seeded {len(scheduled_outages)} scheduled outages.")
    print("Database seeded successfully.")