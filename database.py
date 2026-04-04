# database.py — one place that knows about the DB connection

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import config

engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a session and closes it after the request."""
    db = Session()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    import models  # noqa: ensure models are registered before create_all
    Base.metadata.create_all(bind=engine)
