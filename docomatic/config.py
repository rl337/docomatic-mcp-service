"""Configuration management for Doc-O-Matic.

This module provides configuration settings for the Doc-O-Matic application.
All configuration values can be overridden via environment variables or .env file.

Environment Variables:
    DATABASE_URL: Database connection URL (default: sqlite:///./docomatic.db)
                  Examples:
                  - SQLite: sqlite:///./docomatic.db
                  - PostgreSQL: postgresql://user:pass@localhost/dbname
    DB_POOL_SIZE: Connection pool size (default: 5)
    DB_MAX_OVERFLOW: Maximum overflow connections (default: 10)
    DB_POOL_TIMEOUT: Connection timeout in seconds (default: 30)
    SQL_ECHO: Enable SQL query logging for debugging (default: false)
              Set to "true" to enable SQL query logging
    GITHUB_TOKEN: GitHub API token for export functionality (optional)
    LOG_LEVEL: Logging level (default: INFO)
    LOG_FORMAT: Logging format (default: json)
    ENVIRONMENT: Environment name (default: development)
    DEBUG: Enable debug mode (default: false)
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for Doc-O-Matic.
    
    All configuration values can be set via environment variables or .env file.
    Defaults are provided for development convenience.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database configuration
    database_url: str = "sqlite:///./docomatic.db"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    sql_echo: bool = False

    # GitHub integration
    github_token: Optional[str] = None

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"

    # Environment configuration
    environment: str = "development"
    debug: bool = False

    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL."""
        return self.database_url.startswith("postgresql")

    def is_sqlite(self) -> bool:
        """Check if using SQLite."""
        return self.database_url.startswith("sqlite")

    def get_database_url(self) -> str:
        """Get the database URL."""
        return self.database_url

    def get_github_token(self) -> Optional[str]:
        """Get the GitHub token from settings."""
        return self.github_token


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)."""
    return Settings()


# Backward compatibility: Keep Config class for existing code
# These will be deprecated in favor of get_settings()
class Config:
    """Legacy configuration class for backward compatibility.
    
    DEPRECATED: Use get_settings() instead.
    This class is maintained for backward compatibility during migration.
    """

    @classmethod
    def get_database_url(cls) -> str:
        """Get the database URL."""
        return get_settings().get_database_url()

    @classmethod
    def get_github_token(cls) -> Optional[str]:
        """Get the GitHub token from environment."""
        return get_settings().get_github_token()

    @classmethod
    def is_postgresql(cls) -> bool:
        """Check if using PostgreSQL."""
        return get_settings().is_postgresql()

    @classmethod
    def is_sqlite(cls) -> bool:
        """Check if using SQLite."""
        return get_settings().is_sqlite()
