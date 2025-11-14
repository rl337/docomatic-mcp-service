"""Storage layer for Doc-O-Matic."""

from docomatic.storage.database import Database, get_db
from docomatic.storage.repositories import (
    DocumentRepository,
    LinkRepository,
    SectionRepository,
)

__all__ = [
    "Database",
    "get_db",
    "DocumentRepository",
    "SectionRepository",
    "LinkRepository",
]
