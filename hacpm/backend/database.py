import os
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger("hacpm")

DB_PATH = os.environ.get("HACPM_DB_PATH", "/data/db/hacpm.sqlite")

engine = create_async_engine(
    f"sqlite+aiosqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# Schema version tracks which migrations have been applied.
# Bump this when adding new migrations.
SCHEMA_VERSION = 2


def _get_table_columns(connection, table_name):
    """Get column names for a table."""
    result = connection.execute(text(f"PRAGMA table_info({table_name})"))
    return [row[1] for row in result.fetchall()]


def _table_exists(connection, table_name):
    """Check if a table exists in the database."""
    result = connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name},
    )
    return result.fetchone() is not None


def _get_schema_version(connection):
    """Get the current schema version from the DB, or 0 if not tracked yet."""
    if not _table_exists(connection, "schema_version"):
        connection.execute(text(
            "CREATE TABLE schema_version (version INTEGER NOT NULL)"
        ))
        connection.execute(text("INSERT INTO schema_version (version) VALUES (0)"))
        return 0
    result = connection.execute(text("SELECT version FROM schema_version"))
    row = result.fetchone()
    return row[0] if row else 0


def _set_schema_version(connection, version):
    """Update the schema version."""
    connection.execute(text("UPDATE schema_version SET version = :v"), {"v": version})


def _migrate_db_sync(connection):
    """
    Apply all pending schema migrations.

    Each migration is idempotent — safe to run even if already applied.
    The schema_version table tracks which migrations have run so we skip
    already-applied ones on future startups.
    """
    current = _get_schema_version(connection)
    logger.info(f"Database schema version: {current}, target: {SCHEMA_VERSION}")

    if current >= SCHEMA_VERSION:
        logger.info("Database is up to date.")
        return

    # ── Migration 1: Add thumbnail_path to task_photos ──
    if current < 1:
        if _table_exists(connection, "task_photos"):
            columns = _get_table_columns(connection, "task_photos")
            if "thumbnail_path" not in columns:
                connection.execute(text(
                    "ALTER TABLE task_photos ADD COLUMN thumbnail_path VARCHAR(500)"
                ))
                logger.info("Migration 1: added thumbnail_path to task_photos")
        _set_schema_version(connection, 1)

    # ── Migration 2: Drop display_name from users (SQLite workaround) ──
    # SQLite doesn't support DROP COLUMN before 3.35.0, so we just leave
    # the old column in place — the code no longer reads or writes it.
    # This migration only marks the version as applied.
    if current < 2:
        logger.info("Migration 2: display_name column ignored (code no longer uses it)")
        _set_schema_version(connection, 2)

    logger.info(f"Migrations complete. Schema version is now {SCHEMA_VERSION}.")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_db_sync)


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
