import os

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


load_dotenv()


# NOTE: the old default pointed at "localhost", which only works when
# Postgres runs on the same host as the app. Inside docker-compose the
# database is a separate container reachable by its service name, so
# the default here is updated to match docker-compose.yml's service
# name ("db"). DATABASE_URL from the environment always wins -- this
# default only matters if the env var is unset entirely.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:hellosql@db:5432/power_grid_db"
)

# echo=True (SQL logging) is useful locally but noisy and slightly
# slower under real load (39 msg/s steady state, bursts of thousands).
# Controlled by env so it can be left on in dev and off in the
# deployed/public URL.
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"


engine = create_engine(
    DATABASE_URL,
    echo=SQL_ECHO,
    # pool_pre_ping avoids "server closed the connection unexpectedly"
    # errors after Postgres restarts or an idle connection is reaped --
    # a real failure mode on free-tier hosting where the DB can be
    # recycled independently of the app container.
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()