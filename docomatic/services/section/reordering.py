"""Section reordering operations."""

from typing import Any

from sqlalchemy.orm import Session

from docomatic.exceptions import (
    DatabaseError,
    NotFoundError,
    ValidationError,
)
from docomatic.models.section import Section
from docomatic.storage.repositories import SectionRepository


class SectionReorderer:
    """Handles section reordering and parent updates."""

    def __init__(self, session: Session, section_repo: SectionRepository):
        """
        Initialize reorderer with session and repository.

        Args:
            session: SQLAlchemy database session
            section_repo: Section repository for data access
        """
        self.session = session
        self.section_repo = section_repo

    def update_parent(
        self,
        section_id: str,
        new_parent_section_id: str | None,
        order_index: int | None = None,
    ) -> Section:
        """
        Move a section to a different parent (or make it top-level).

        Args:
            section_id: Section ID to move
            new_parent_section_id: New parent section ID (None for top-level)
            order_index: Optional new order index (auto-incremented if not provided)

        Returns:
            Updated section with new parent

        Raises:
            ValidationError: If section_id or new_parent_section_id is invalid, or if cycle detected
            NotFoundError: If section or new parent is not found
            DatabaseError: If database operation fails
        """
        try:
            section = self.section_repo.get_by_id(section_id)
            if section is None:
                raise NotFoundError("Section", section_id)

            # Verify new parent exists if provided
            if new_parent_section_id is not None:
                new_parent = self.section_repo.get_by_id(new_parent_section_id)
                if new_parent is None:
                    raise NotFoundError("Section", new_parent_section_id)
                # Verify new parent belongs to same document
                if new_parent.document_id != section.document_id:
                    raise ValidationError(
                        "New parent section must belong to the same document",
                        "new_parent_section_id",
                    )

            # Calculate order_index if not provided
            if order_index is None:
                siblings = (
                    self.section_repo.get_children(new_parent_section_id)
                    if new_parent_section_id
                    else self.section_repo.get_by_document_id(section.document_id, flat=False)
                )
                # Exclude current section from siblings count
                siblings = [s for s in siblings if s.id != section_id]
                if siblings:
                    order_index = max(s.order_index for s in siblings) + 1
                else:
                    order_index = 0

            # Update parent and order
            section.parent_section_id = new_parent_section_id
            section.order_index = order_index

            self.section_repo.update(section)
            self.session.commit()
            return section

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to update parent: {str(e)}", e) from e

    def reorder_sections(
        self,
        parent_section_id: str | None,
        section_order: list[str],
    ) -> list[Section]:
        """
        Reorder sections within a parent.

        Args:
            parent_section_id: Parent section ID (None for top-level sections)
            section_order: List of section IDs in desired order

        Returns:
            List of reordered sections

        Raises:
            ValidationError: If section IDs are invalid or don't belong to parent
            NotFoundError: If parent or any section is not found
            DatabaseError: If database operation fails
        """
        if not isinstance(section_order, list) or not section_order:
            raise ValidationError("section_order must be a non-empty list", "section_order")

        try:
            # Get parent's document_id
            if parent_section_id is not None:
                parent = self.section_repo.get_by_id(parent_section_id)
                if parent is None:
                    raise NotFoundError("Section", parent_section_id)
                document_id = parent.document_id
                siblings = self.section_repo.get_children(parent_section_id)
            else:
                # For top-level sections, we need document_id from first section
                first_section = self.section_repo.get_by_id(section_order[0])
                if first_section is None:
                    raise NotFoundError("Section", section_order[0])
                document_id = first_section.document_id
                siblings = self.section_repo.get_by_document_id(document_id, flat=False)

            # Verify all sections in order belong to the same parent
            sibling_ids = {s.id for s in siblings}
            for section_id in section_order:
                section = self.section_repo.get_by_id(section_id)
                if section is None:
                    raise NotFoundError("Section", section_id)
                if section.parent_section_id != parent_section_id:
                    raise ValidationError(
                        f"Section {section_id} does not belong to parent {parent_section_id}",
                        "section_order",
                    )
                if section.document_id != document_id:
                    raise ValidationError(
                        f"Section {section_id} does not belong to document {document_id}",
                        "section_order",
                    )

            # Update order_index for each section
            updated_sections = []
            for order_index, section_id in enumerate(section_order):
                section = self.section_repo.get_by_id(section_id)
                section.order_index = order_index
                self.section_repo.update(section)
                updated_sections.append(section)

            self.session.commit()
            return updated_sections

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to reorder sections: {str(e)}", e) from e
