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


def _migrate_db_sync(connection):
    """Apply schema migrations for existing databases (runs in sync context)."""
    try:
        result = connection.execute(text("PRAGMA table_info(task_photos)"))
        columns = [row[1] for row in result.fetchall()]
        if columns and "thumbnail_path" not in columns:
            connection.execute(
                text("ALTER TABLE task_photos ADD COLUMN thumbnail_path VARCHAR(500)")
            )
            logger.info("Migration: added thumbnail_path column to task_photos")
    except Exception as e:
        logger.debug(f"Migration check for task_photos: {e}")


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
