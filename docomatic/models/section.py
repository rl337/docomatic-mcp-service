"""Section model for storing hierarchical document sections."""

from typing import Any, Optional

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from docomatic.models.base import Base, TimestampMixin


class Section(Base, TimestampMixin):
    """Section model representing a hierarchical section within a document."""

    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_section_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    heading: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    # Use 'meta' as Python attribute name to avoid SQLAlchemy reserved name conflict
    # Database column is still 'metadata' for compatibility
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="sections")
    parent_section: Mapped[Optional["Section"]] = relationship(
        "Section", remote_side=[id], back_populates="child_sections"
    )
    child_sections: Mapped[list["Section"]] = relationship(
        "Section", back_populates="parent_section", cascade="all, delete-orphan"
    )
    links: Mapped[list["Link"]] = relationship(
        "Link", back_populates="section", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Section(id={self.id!r}, heading={self.heading!r}, document_id={self.document_id!r})>"
