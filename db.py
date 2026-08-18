"""DB Engine and Session Factory creation functions."""

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def make_engine(db_path: str = "bot.db") -> AsyncEngine:
    """Create an async engine for the database.

    Args:
        db_path: The path to the SQLite database file.

    Returns:
        An AsyncEngine instance connected to the specified SQLite database.
    """
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")  # safe + faster with WAL
        cursor.execute("PRAGMA foreign_keys=ON")  # SQLite defaults this off
        cursor.close()

    return engine


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory for the database.

    Args:
        engine: The AsyncEngine instance to bind the session factory to.

    Returns:
        An async_sessionmaker instance for creating AsyncSession objects.
    """
    return async_sessionmaker(engine, expire_on_commit=False)
