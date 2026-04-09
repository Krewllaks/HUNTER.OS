"""
HUNTER.OS / ARES - Database Engine (SQLite + PostgreSQL)
Dual-backend support: SQLite for dev, PostgreSQL for prod.
Detected automatically from DATABASE_URL prefix.
"""
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Detect backend ────────────────────────────────────────
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_is_postgres = settings.DATABASE_URL.startswith("postgresql")

# ── Engine kwargs per backend ─────────────────────────────
_engine_kwargs: dict = {"echo": False}  # SQL logging off — too noisy even in debug

# Suppress SQLAlchemy engine logger (even when other loggers are DEBUG)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)

if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    logger.info("Database backend: SQLite")

elif _is_postgres:
    _engine_kwargs.update(
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    logger.info("Database backend: PostgreSQL")

else:
    # Unknown backend - let SQLAlchemy handle it with no extras
    logger.warning("Unknown database backend: %s", settings.DATABASE_URL.split("://")[0])

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

# ── SQLite PRAGMAs (only for SQLite) ─────────────────────
if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency - yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables on startup + lightweight column migrations."""
    Base.metadata.create_all(bind=engine)
    _migrate_add_columns()


def _migrate_add_columns():
    """Add missing columns to existing tables (safe for SQLite + PostgreSQL)."""
    from sqlalchemy import text, inspect

    insp = inspect(engine)
    _add_column_if_missing(insp, "products", "analysis_cache", "JSON")


def _add_column_if_missing(inspector, table: str, column: str, col_type: str):
    """ALTER TABLE ADD COLUMN only if column does not exist yet."""
    from sqlalchemy import text

    if table not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
    logger.info(f"Migration: added column {table}.{column} ({col_type})")
