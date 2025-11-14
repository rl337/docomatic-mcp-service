"""Document service layer for business logic and validation."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from docomatic.exceptions import (
    DatabaseError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from docomatic.models.document import Document
from docomatic.models.section import Section
from docomatic.storage.repositories import DocumentRepository, LinkRepository, SectionRepository


class DocumentService:
    """Service layer for document CRUD operations with validation and error handling."""

    # Validation constants
    TITLE_MIN_LENGTH = 1
    TITLE_MAX_LENGTH = 500
    ID_MAX_LENGTH = 255

    def __init__(self, session: Session):
        """
        Initialize document service with database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.document_repo = DocumentRepository(session)
        self.section_repo = SectionRepository(session)
        self.link_repo = LinkRepository(session)

    def create_document(
        self,
        title: str,
        metadata: dict[str, Any] | None = None,
        document_id: str | None = None,
        initial_sections: list[dict[str, Any]] | None = None,
    ) -> Document:
        """
        Create a new document.

        Args:
            title: Document title (required, non-empty)
            metadata: Optional document metadata (JSON structure)
            document_id: Optional document ID. If not provided, generates a UUID.
            initial_sections: Optional list of initial sections to create.
                             Each section dict should have: heading, body, order_index,
                             parent_section_id (optional), metadata (optional)

        Returns:
            Created document with ID

        Raises:
            ValidationError: If title is invalid or metadata is invalid
            DuplicateError: If document with same ID already exists
            DatabaseError: If database operation fails
        """
        # Validate title
        self._validate_title(title)

        # Validate metadata
        if metadata is not None:
            self._validate_metadata(metadata)

        # Generate ID if not provided
        if document_id is None:
            document_id = str(uuid.uuid4())
        else:
            self._validate_id(document_id)

        # Check for duplicate ID
        existing = self.document_repo.get_by_id(document_id)
        if existing is not None:
            raise DuplicateError("Document", "id", document_id)

        try:
            # Create document
            document = Document(
                id=document_id,
                title=title,
                metadata=metadata or {},
            )
            self.document_repo.create(document)

            # Create initial sections if provided
            if initial_sections:
                self._create_initial_sections(document.id, initial_sections)

            self.session.commit()
            return document

        except (DuplicateError, ValidationError):
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to create document: {str(e)}", e) from e

    def get_document(
        self,
        document_id: str,
        include_sections: bool = True,
        include_links: bool = True,
    ) -> Document:
        """
        Get document by ID with optional sections and links.

        Args:
            document_id: Document ID
            include_sections: If True, include all sections in tree structure
            include_links: If True, include document-level links

        Returns:
            Document with sections and links loaded

        Raises:
            ValidationError: If document_id is invalid
            NotFoundError: If document is not found
            DatabaseError: If database operation fails
        """
        self._validate_id(document_id)

        try:
            if include_sections:
                document = self.document_repo.get_by_id_with_sections(document_id)
                if document:
                    # Load section tree
                    document.sections = self.section_repo.get_section_tree_by_document(
                        document_id
                    )
            else:
                document = self.document_repo.get_by_id(document_id)

            if document is None:
                raise NotFoundError("Document", document_id)

            # Load document-level links if requested
            if include_links:
                document.links = self.link_repo.get_by_document_id(document_id)

            return document

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get document: {str(e)}", e) from e

    def update_document(
        self,
        document_id: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """
        Update document title and/or metadata.

        Args:
            document_id: Document ID
            title: New title (optional)
            metadata: New metadata (optional, replaces existing)

        Returns:
            Updated document

        Raises:
            ValidationError: If document_id, title, or metadata is invalid
            NotFoundError: If document is not found
            DatabaseError: If database operation fails
        """
        self._validate_id(document_id)

        # Validate title if provided
        if title is not None:
            self._validate_title(title)

        # Validate metadata if provided
        if metadata is not None:
            self._validate_metadata(metadata)

        try:
            document = self.document_repo.get_by_id(document_id)
            if document is None:
                raise NotFoundError("Document", document_id)

            # Update fields
            if title is not None:
                document.title = title
            if metadata is not None:
                document.meta = metadata

            self.document_repo.update(document)
            self.session.commit()
            return document

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to update document: {str(e)}", e) from e

    def delete_document(
        self, document_id: str, soft_delete: bool = False, validate_references: bool = True
    ) -> bool:
        """
        Delete a document and all associated sections and links.

        Args:
            document_id: Document ID
            soft_delete: If True, mark as deleted but preserve in database (not implemented yet)
            validate_references: If True, validate no external references before hard delete

        Returns:
            True if document was deleted, False if not found

        Raises:
            ValidationError: If document_id is invalid
            DatabaseError: If database operation fails or external references exist
        """
        self._validate_id(document_id)

        try:
            document = self.document_repo.get_by_id(document_id)
            if document is None:
                return False

            # Soft delete (future enhancement - would require adding deleted_at field)
            if soft_delete:
                # For now, soft delete is not implemented
                # Would need to add deleted_at timestamp field to Document model
                raise NotImplementedError("Soft delete not yet implemented")

            # Validate external references if requested
            if validate_references:
                # Check for links that might be referenced externally
                # This is a placeholder - actual validation would check external systems
                pass

            # Hard delete (cascades to sections and links via foreign keys)
            self.document_repo.delete(document_id)
            self.session.commit()
            return True

        except (ValidationError, NotImplementedError):
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to delete document: {str(e)}", e) from e

    def list_documents(
        self,
        title_pattern: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        List documents with optional filtering and pagination.

        Args:
            title_pattern: Optional title pattern to filter by (case-insensitive substring match)
            metadata_filter: Optional metadata filter (checks if metadata contains all key-value pairs)
            limit: Maximum number of documents to return (default: 100)
            offset: Number of documents to skip (default: 0)

        Returns:
            List of document summaries with:
            - id: Document ID
            - title: Document title
            - section_count: Number of sections
            - updated_at: Last update timestamp

        Raises:
            ValidationError: If limit or offset is invalid
            DatabaseError: If database operation fails
        """
        # Validate pagination parameters
        if limit < 0:
            raise ValidationError("limit must be non-negative", "limit")
        if offset < 0:
            raise ValidationError("offset must be non-negative", "offset")

        try:
            # Get documents based on filters
            if title_pattern:
                documents = self.document_repo.search_by_title(title_pattern, limit=limit)
            else:
                documents = self.document_repo.get_all(limit=limit, offset=offset)

            # Apply metadata filter if provided
            if metadata_filter:
                documents = [
                    doc
                    for doc in documents
                    if self._metadata_matches(doc.meta or {}, metadata_filter)
                ]

            # Build summaries
            summaries = []
            for doc in documents:
                # Count sections
                section_count = len(
                    self.section_repo.get_by_document_id(doc.id, flat=True)
                )

                summaries.append(
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "section_count": section_count,
                        "updated_at": doc.updated_at,
                    }
                )

            return summaries

        except ValidationError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to list documents: {str(e)}", e) from e

    def _create_initial_sections(
        self, document_id: str, sections: list[dict[str, Any]]
    ) -> None:
        """Create initial sections for a document."""
        for section_data in sections:
            # Validate required fields
            if "heading" not in section_data:
                raise ValidationError("Section heading is required", "heading")
            if "body" not in section_data:
                raise ValidationError("Section body is required", "body")

            # Generate section ID
            section_id = section_data.get("id") or str(uuid.uuid4())
            self._validate_id(section_id)

            # Validate parent_section_id if provided
            parent_section_id = section_data.get("parent_section_id")
            if parent_section_id:
                self._validate_id(parent_section_id)
                # Verify parent exists
                parent = self.section_repo.get_by_id(parent_section_id)
                if parent is None:
                    raise NotFoundError("Section", parent_section_id)

            # Create section
            section = Section(
                id=section_id,
                document_id=document_id,
                parent_section_id=parent_section_id,
                heading=section_data["heading"],
                body=section_data["body"],
                order_index=section_data.get("order_index", 0),
                metadata=section_data.get("metadata") or {},
            )
            self.section_repo.create(section)

    def _validate_title(self, title: str) -> None:
        """Validate document title."""
        if not isinstance(title, str):
            raise ValidationError("Title must be a string", "title")
        if not title or not title.strip():
            raise ValidationError("Title is required and cannot be empty", "title")
        if len(title) < self.TITLE_MIN_LENGTH:
            raise ValidationError(
                f"Title must be at least {self.TITLE_MIN_LENGTH} character(s)", "title"
            )
        if len(title) > self.TITLE_MAX_LENGTH:
            raise ValidationError(
                f"Title must be at most {self.TITLE_MAX_LENGTH} characters", "title"
            )

    def _validate_id(self, document_id: str) -> None:
        """Validate document ID."""
        if not isinstance(document_id, str):
            raise ValidationError("Document ID must be a string", "id")
        if not document_id or not document_id.strip():
            raise ValidationError("Document ID cannot be empty", "id")
        if len(document_id) > self.ID_MAX_LENGTH:
            raise ValidationError(
                f"Document ID must be at most {self.ID_MAX_LENGTH} characters", "id"
            )

    def _validate_metadata(self, metadata: dict[str, Any]) -> None:
        """Validate metadata structure."""
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a dictionary", "metadata")
        # Additional validation could check for specific keys or value types
        # For now, we just ensure it's a dict (JSON-compatible)

    def _metadata_matches(
        self, document_metadata: dict[str, Any], filter_metadata: dict[str, Any]
    ) -> bool:
        """Check if document metadata matches filter metadata."""
        for key, value in filter_metadata.items():
            if key not in document_metadata:
                return False
            if document_metadata[key] != value:
                return False
        return True
