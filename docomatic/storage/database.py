"""Database connection and configuration management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from docomatic.config import get_settings
from docomatic.models.base import Base


class Database:
    """Database connection manager with connection pooling and transaction handling."""

    def __init__(self, database_url: str | None = None, pool_size: int | None = None, max_overflow: int | None = None):
        """
        Initialize database connection.

        Args:
            database_url: Database connection URL. If None, reads from settings.
                         Supports PostgreSQL and SQLite.
            pool_size: Number of connections to maintain in the pool. If None, uses settings.
            max_overflow: Maximum number of connections to allow beyond pool_size. If None, uses settings.
        """
        settings = get_settings()
        
        if database_url is None:
            database_url = settings.get_database_url()
        
        if pool_size is None:
            pool_size = settings.db_pool_size
        
        if max_overflow is None:
            max_overflow = settings.db_max_overflow

        # Configure connection pooling
        connect_args = {}
        if database_url.startswith("sqlite"):
            # SQLite-specific configuration
            connect_args = {"check_same_thread": False}
            # Enable foreign keys for SQLite
            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        self.engine = create_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_pre_ping=True,  # Verify connections before using
            connect_args=connect_args,
            echo=settings.sql_echo,
        )

        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self) -> None:
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions with automatic transaction handling.

        Usage:
            with db.session() as session:
                # Use session here
                session.commit()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """
        Get a database session. Caller is responsible for closing.

        Returns:
            Database session
        """
        return self.SessionLocal()

    def execute_raw_sql(self, sql: str, params: dict | None = None) -> any:
        """
        Execute raw SQL query.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        with self.session() as session:
            result = session.execute(text(sql), params or {})
            return result.fetchall()


# Global database instance
_db: Database | None = None


def get_db(database_url: str | None = None) -> Database:
    """
    Get or create the global database instance.

    Args:
        database_url: Database connection URL. Only used on first call.

    Returns:
        Database instance
    """
    global _db
    if _db is None:
        _db = Database(database_url)
    return _db


def reset_db() -> None:
    """Reset the global database instance (useful for testing)."""
    global _db
    _db = None
