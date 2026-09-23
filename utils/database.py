"""Database connection, session management, and table initialization."""

from contextlib import contextmanager
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from sqlalchemy.pool import StaticPool

DEFAULT_DB_URL = os.environ.get("DATABASE_URL", "sqlite:///cadence.db")

Base = declarative_base()

_engine = None
_session_factory = None


def get_engine(db_url: str | None = None):
    """Get or create the SQLAlchemy engine."""
    global _engine, _session_factory
    target_url = db_url or DEFAULT_DB_URL
    if _engine is None or (db_url is not None and str(_engine.url) != target_url):
        if target_url == "sqlite:///:memory:":
            _engine = create_engine(target_url, connect_args={"check_same_thread": False}, poolclass=StaticPool, echo=False)
        else:
            connect_args = {"check_same_thread": False} if target_url.startswith("sqlite") else {}
            _engine = create_engine(target_url, connect_args=connect_args, echo=False)
        _session_factory = None
    return _engine


def get_session_factory(db_url: str | None = None):
    """Get or create the scoped session factory."""
    global _session_factory
    engine = get_engine(db_url)
    if _session_factory is None:
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        _session_factory = scoped_session(factory)
    return _session_factory


@contextmanager
def get_db(db_url: str | None = None):
    """Provide a transactional scope around a series of operations."""
    session_factory = get_session_factory(db_url)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(db_url: str | None = None):
    """Initialize database tables."""
    engine = get_engine(db_url)
    Base.metadata.create_all(bind=engine)
