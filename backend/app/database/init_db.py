from app.database.database import Base
from app.database.database import engine

# Import all models so SQLAlchemy registers them

from app.models.transformer import Transformer
from app.models.pole import Pole
from app.models.telemetry import Telemetry
from app.models.incident import Incident
from app.models.ticket import Ticket
from app.models.scheduled_outage import ScheduledOutage


def create_tables():

    print("=" * 60)
    print("Creating database tables...")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)

    print("=" * 60)
    print("Database tables created successfully.")
    print("=" * 60)


if __name__ == "__main__":

    create_tables()