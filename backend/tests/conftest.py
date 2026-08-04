import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base

# Import every model so Base.metadata knows about all tables --
# without these imports create_all() would silently skip tables
# whose model module was never loaded.
from app.models.transformer import Transformer  # noqa: F401
from app.models.pole import Pole  # noqa: F401
from app.models.telemetry import Telemetry  # noqa: F401
from app.models.incident import Incident  # noqa: F401
from app.models.ticket import Ticket  # noqa: F401
from app.models.scheduled_outage import ScheduledOutage  # noqa: F401


@pytest.fixture()
def db():
    """
    Fresh in-memory SQLite database per test. No Postgres, no
    docker-compose required to run the test suite -- this is what CI
    or a reviewer running `pytest` cold should be able to use with
    zero setup.

    NOTE: SQLite does not enforce all Postgres constraints the same
    way (e.g. some FK pragmas need enabling), but for the logic under
    test here (localization/classification, pure Python + querying)
    that difference doesn't matter -- we're not testing SQL-level
    constraint enforcement.
    """

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    session = session_local()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def make_transformer(
    db,
    transformer_id="DT0001",
    feeder_id="F001",
    lat=18.5204,
    lon=73.8567,
    pincode="411001",
):
    transformer = Transformer(
        transformer_id=transformer_id,
        feeder_id=feeder_id,
        name=f"Transformer {transformer_id}",
        latitude=lat,
        longitude=lon,
        pincode=pincode,
    )
    db.add(transformer)
    db.flush()
    return transformer


def make_pole(
    db,
    pole_id,
    transformer,
    parent=None,
    lat=18.5204,
    lon=73.8567,
    pincode="411001",
    energized=True,
    has_device=True,
    active=True,
):
    """
    Builds a single pole with sane defaults, wired to `parent` (another
    Pole instance, or None for a root pole directly off the
    transformer). `has_device=False` mimics the ~9% of poles with no
    telemetry device fitted -- these should never be trusted as
    direct evidence of a fault.
    """
    pole = Pole(
        pole_id=pole_id,
        transformer_id=transformer.id,
        parent_pole_id=parent.id if parent else None,
        latitude=lat,
        longitude=lon,
        pincode=pincode,
        energized=energized,
        active=active,
        last_device_id=(f"DEV-{pole_id}" if has_device else None),
        last_applied_seq=(1 if has_device else None),
    )
    db.add(pole)
    db.flush()
    return pole


def make_line(
    db,
    transformer,
    pole_ids,
    start_lat=18.5204,
    start_lon=73.8567,
    lat_step=0.0004,
    energized=True,
    has_device=True,
):
    """
    Convenience: builds a simple straight chain of poles
    (pole_ids[0] -> pole_ids[1] -> ... ) all directly under
    `transformer`, all energized/has_device the same way unless
    overridden pole-by-pole afterwards by the caller.
    """
    poles = []
    parent = None

    for i, pole_id in enumerate(pole_ids):
        pole = make_pole(
            db,
            pole_id=pole_id,
            transformer=transformer,
            parent=parent,
            lat=start_lat + lat_step * i,
            lon=start_lon,
            energized=energized,
            has_device=has_device,
        )
        poles.append(pole)
        parent = pole

    return poles