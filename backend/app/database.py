from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def _configure_sqlite(dbapi_connection, _connection_record) -> None:
    """On SQLite, wait on a locked DB instead of immediately erroring, and use
    WAL so a reader does not block a writer. This makes the concurrent writes a
    pilot can produce (two students saving at once) resilient rather than raising
    'database is locked'."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def make_engine(database_url: str):
    url = normalize_database_url(database_url)
    is_sqlite = url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(url, connect_args=connect_args, future=True)
    if is_sqlite:
        event.listen(engine, "connect", _configure_sqlite)
    return engine


def make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.SessionLocal
    with session_factory() as db:
        yield db


def get_app_settings(request: Request):
    return request.app.state.settings
