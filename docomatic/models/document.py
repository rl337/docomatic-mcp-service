"""Document model for storing documents."""

from typing import Any, Optional

from sqlalchemy import JSON, String, Text, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from docomatic.models.base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    """Document model representing a structured Markdown document."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    # Use 'meta' as Python attribute name to avoid SQLAlchemy reserved name conflict
    # Database column is still 'metadata' for compatibility
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )

    # Relationships
    sections: Mapped[list["Section"]] = relationship(
        "Section", back_populates="document", cascade="all, delete-orphan"
    )
    links: Mapped[list["Link"]] = relationship(
        "Link", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id!r}, title={self.title!r})>"
