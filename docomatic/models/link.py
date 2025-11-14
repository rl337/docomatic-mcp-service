"""Link model for storing external links."""

from typing import Any, Optional

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from docomatic.models.base import Base, TimestampMixin


class Link(Base, TimestampMixin):
    """Link model representing external links to To-Do-Rama, Bucket-O-Facts, or GitHub."""

    __tablename__ = "links"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    section_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    link_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'todo-rama', 'bucket-o-facts', 'github'
    link_target: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    link_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True, default=dict
    )

    # Relationships
    section: Mapped[Optional["Section"]] = relationship("Section", back_populates="links")
    document: Mapped[Optional["Document"]] = relationship("Document", back_populates="links")

    def __repr__(self) -> str:
        return f"<Link(id={self.id!r}, link_type={self.link_type!r}, link_target={self.link_target!r})>"
