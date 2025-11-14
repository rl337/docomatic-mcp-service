"""Section service layer for business logic and validation."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from docomatic.exceptions import (
    DatabaseError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from docomatic.models.section import Section
from docomatic.storage.repositories import LinkRepository, SectionRepository
from docomatic.services.section.reordering import SectionReorderer
from docomatic.services.section.tree_operations import SectionTreeBuilder
from docomatic.services.section.validation import SectionValidator


class SectionService:
    """Service layer for section CRUD operations with validation and error handling."""

    def __init__(self, session: Session):
        """
        Initialize section service with database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.section_repo = SectionRepository(session)
        self.link_repo = LinkRepository(session)
        self.validator = SectionValidator()
        self.tree_builder = SectionTreeBuilder(self.section_repo)
        self.reorderer = SectionReorderer(self.session, self.section_repo)

    def create_section(
        self,
        document_id: str,
        heading: str,
        body: str,
        parent_section_id: str | None = None,
        order_index: int | None = None,
        metadata: dict[str, Any] | None = None,
        section_id: str | None = None,
    ) -> Section:
        """
        Create a new section.

        Args:
            document_id: Document ID (required)
            heading: Section heading (required, non-empty)
            body: Section body content (required)
            parent_section_id: Optional parent section ID for nesting
            order_index: Order within parent (default: 0)
            metadata: Optional section metadata (JSON structure)
            section_id: Optional section ID. If not provided, generates a UUID.

        Returns:
            Created section with ID

        Raises:
            ValidationError: If heading, body, or IDs are invalid
            NotFoundError: If document or parent section is not found
            DuplicateError: If section with same ID already exists
            DatabaseError: If database operation fails
        """
        # Validate heading
        self.validator.validate_heading(heading)

        # Validate body
        self.validator.validate_body(body)

        # Validate document_id
        self.validator.validate_id(document_id)

        # Validate parent_section_id if provided
        if parent_section_id is not None:
            self.validator.validate_id(parent_section_id)
            # Verify parent exists
            parent = self.section_repo.get_by_id(parent_section_id)
            if parent is None:
                raise NotFoundError("Section", parent_section_id)
            # Verify parent belongs to same document
            if parent.document_id != document_id:
                raise ValidationError(
                    "Parent section must belong to the same document", "parent_section_id"
                )

        # Validate metadata
        if metadata is not None:
            self.validator.validate_metadata(metadata)

        # Generate ID if not provided
        if section_id is None:
            section_id = str(uuid.uuid4())
        else:
            self.validator.validate_id(section_id)

        # Check for duplicate ID
        existing = self.section_repo.get_by_id(section_id)
        if existing is not None:
            raise DuplicateError("Section", "id", section_id)

        # Auto-increment order_index if not explicitly provided
        if order_index is None:
            # Get max order_index for siblings (same parent)
            siblings = (
                self.section_repo.get_children(parent_section_id)
                if parent_section_id
                else self.section_repo.get_by_document_id(document_id, flat=False)
            )
            if siblings:
                order_index = max(s.order_index for s in siblings) + 1
            else:
                order_index = 0

        try:
            # Create section
            section = Section(
                id=section_id,
                document_id=document_id,
                parent_section_id=parent_section_id,
                heading=heading,
                body=body,
                order_index=order_index,
                metadata=metadata or {},
            )
            self.section_repo.create(section)
            self.session.commit()
            return section

        except (DuplicateError, ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to create section: {str(e)}", e) from e

    def get_section(
        self,
        section_id: str,
        include_children: bool = True,
        include_links: bool = True,
    ) -> Section:
        """
        Get section by ID with optional children and links.

        Args:
            section_id: Section ID
            include_children: If True, include all children in tree structure
            include_links: If True, include section links

        Returns:
            Section with children and links loaded

        Raises:
            ValidationError: If section_id is invalid
            NotFoundError: If section is not found
            DatabaseError: If database operation fails
        """
        self.validator.validate_id(section_id)

        try:
            if include_children:
                section = self.section_repo.get_section_tree(section_id)
            else:
                section = self.section_repo.get_by_id(section_id)

            if section is None:
                raise NotFoundError("Section", section_id)

            # Load links if requested
            if include_links:
                section.links = self.link_repo.get_by_section_id(section_id)

            return section

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get section: {str(e)}", e) from e

    def update_section(
        self,
        section_id: str,
        heading: str | None = None,
        body: str | None = None,
        order_index: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Section:
        """
        Update section heading, body, order_index, and/or metadata.

        Args:
            section_id: Section ID
            heading: New heading (optional)
            body: New body (optional)
            order_index: New order index (optional)
            metadata: New metadata (optional, replaces existing)

        Returns:
            Updated section

        Raises:
            ValidationError: If section_id, heading, or metadata is invalid
            NotFoundError: If section is not found
            DatabaseError: If database operation fails
        """
        self.validator.validate_id(section_id)

        # Validate heading if provided
        if heading is not None:
            self.validator.validate_heading(heading)

        # Validate body if provided
        if body is not None:
            self.validator.validate_body(body)

        # Validate metadata if provided
        if metadata is not None:
            self.validator.validate_metadata(metadata)

        try:
            section = self.section_repo.get_by_id(section_id)
            if section is None:
                raise NotFoundError("Section", section_id)

            # Update fields
            if heading is not None:
                section.heading = heading
            if body is not None:
                section.body = body
            if order_index is not None:
                section.order_index = order_index
            if metadata is not None:
                section.meta = metadata

            self.section_repo.update(section)
            self.session.commit()
            return section

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to update section: {str(e)}", e) from e

    def delete_section(self, section_id: str) -> bool:
        """
        Delete a section and all its children.

        Args:
            section_id: Section ID

        Returns:
            True if section was deleted, False if not found

        Raises:
            ValidationError: If section_id is invalid
            DatabaseError: If database operation fails
        """
        self.validator.validate_id(section_id)

        try:
            # Delete cascades to children via foreign key
            deleted = self.section_repo.delete(section_id)
            if deleted:
                self.session.commit()
            return deleted

        except ValidationError:
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to delete section: {str(e)}", e) from e

    def get_sections_by_document(
        self,
        document_id: str,
        flat: bool = False,
        heading_pattern: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[Section]:
        """
        Get all sections for a document with optional filtering.

        Args:
            document_id: Document ID
            flat: If True, return flat list. If False, return tree structure.
            heading_pattern: Optional heading pattern to filter by (case-insensitive substring match)
            metadata_filter: Optional metadata filter (checks if metadata contains all key-value pairs)

        Returns:
            List of sections (tree or flat)

        Raises:
            ValidationError: If document_id is invalid
            DatabaseError: If database operation fails
        """
        self.validator.validate_id(document_id)

        try:
            return self.tree_builder.build_tree_with_filters(
                document_id,
                flat=flat,
                heading_pattern=heading_pattern,
                metadata_filter=metadata_filter,
            )

        except ValidationError:
            raise
        except Exception as e:
            raise DatabaseError(
                f"Failed to get sections by document: {str(e)}", e
            ) from e

    def search_sections(
        self,
        query: str,
        document_id: str | None = None,
        limit: int = 100,
    ) -> list[Section]:
        """
        Full-text search across section headings and bodies.

        Args:
            query: Search query string
            document_id: Optional document ID to limit search
            limit: Maximum number of results (default: 100)

        Returns:
            List of matching sections

        Raises:
            ValidationError: If query or limit is invalid
            DatabaseError: If database operation fails
        """
        if not isinstance(query, str) or not query.strip():
            raise ValidationError("Query must be a non-empty string", "query")
        if limit < 0:
            raise ValidationError("limit must be non-negative", "limit")

        try:
            return self.section_repo.full_text_search(
                query, document_id=document_id, limit=limit
            )

        except ValidationError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to search sections: {str(e)}", e) from e

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
        self.validator.validate_id(section_id)

        # Validate new parent if provided
        if new_parent_section_id is not None:
            self.validator.validate_id(new_parent_section_id)
            # Check for circular reference (prevent moving section into its own subtree)
            if self.tree_builder.would_create_cycle(section_id, new_parent_section_id):
                raise ValidationError(
                    "Cannot move section into its own subtree (would create cycle)",
                    "new_parent_section_id",
                )

        return self.reorderer.update_parent(section_id, new_parent_section_id, order_index)

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

        # Validate all section IDs
        for section_id in section_order:
            self.validator.validate_id(section_id)

        return self.reorderer.reorder_sections(parent_section_id, section_order)

    def get_section_path(self, section_id: str) -> list[Section]:
        """
        Get the path from root (document level) to the specified section.

        Args:
            section_id: Section ID

        Returns:
            List of sections from root to the specified section (inclusive)

        Raises:
            ValidationError: If section_id is invalid
            NotFoundError: If section is not found
            DatabaseError: If database operation fails
        """
        self.validator.validate_id(section_id)

        try:
            path = self.section_repo.get_path_to_root(section_id)
            if not path:
                raise NotFoundError("Section", section_id)
            return path

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get section path: {str(e)}", e) from e

    def get_section_tree(self, section_id: str) -> Section:
        """
        Get a section with its entire subtree (all descendants).

        Args:
            section_id: Section ID

        Returns:
            Section with all descendants loaded

        Raises:
            ValidationError: If section_id is invalid
            NotFoundError: If section is not found
            DatabaseError: If database operation fails
        """
        return self.get_section(section_id, include_children=True, include_links=False)

