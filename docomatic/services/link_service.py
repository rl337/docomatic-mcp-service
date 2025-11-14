"""Link service layer for business logic and validation."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from docomatic.exceptions import (
    DatabaseError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from docomatic.models.link import Link
from docomatic.storage.repositories import (
    DocumentRepository,
    LinkRepository,
    SectionRepository,
)
from docomatic.services.link.reporting import LinkReporter
from docomatic.services.link.validation import LinkValidator


class LinkService:
    """Service layer for link CRUD operations with validation and error handling."""

    def __init__(self, session: Session):
        """
        Initialize link service with database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.link_repo = LinkRepository(session)
        self.section_repo = SectionRepository(session)
        self.document_repo = DocumentRepository(session)
        self.validator = LinkValidator()
        self.reporter = LinkReporter(self.link_repo)

    def link_section(
        self,
        section_id: str,
        link_type: str,
        link_target: str,
        link_metadata: dict[str, Any] | None = None,
        link_id: str | None = None,
    ) -> Link:
        """
        Link a section to an external resource (To-Do-Rama, Bucket-O-Facts, or GitHub).

        Args:
            section_id: Section ID (required)
            link_type: Link type ('todo-rama', 'bucket-o-facts', or 'github')
            link_target: Link target (URI or identifier)
            link_metadata: Optional link metadata (JSON structure)
            link_id: Optional link ID. If not provided, generates a UUID.

        Returns:
            Created link with ID

        Raises:
            ValidationError: If section_id, link_type, or link_target is invalid
            NotFoundError: If section is not found
            DuplicateError: If link with same ID already exists
            DatabaseError: If database operation fails
        """
        # Validate section_id
        self.validator.validate_id(section_id)

        # Verify section exists
        section = self.section_repo.get_by_id(section_id)
        if section is None:
            raise NotFoundError("Section", section_id)

        # Validate link_type
        self.validator.validate_link_type(link_type)

        # Validate link_target format
        self.validator.validate_link_target(link_target)
        self.validator.validate_link_target_format(link_type, link_target)

        # Check for duplicate link (same section + link_type + link_target)
        existing_links = self.link_repo.get_by_section_id(section_id)
        for existing in existing_links:
            if existing.link_type == link_type and existing.link_target == link_target:
                raise DuplicateError(
                    "Link",
                    "section_id+link_type+link_target",
                    f"{section_id}+{link_type}+{link_target}",
                )

        # Validate metadata
        if link_metadata is not None:
            self.validator.validate_metadata(link_metadata)

        # Generate ID if not provided
        if link_id is None:
            link_id = str(uuid.uuid4())
        else:
            self.validator.validate_id(link_id)

        # Check for duplicate ID
        existing = self.link_repo.get_by_id(link_id)
        if existing is not None:
            raise DuplicateError("Link", "id", link_id)

        try:
            # Create link
            link = Link(
                id=link_id,
                section_id=section_id,
                document_id=section.document_id,
                link_type=link_type,
                link_target=link_target,
                link_metadata=link_metadata or {},
            )
            self.link_repo.create(link)
            self.session.commit()
            return link

        except (DuplicateError, ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to link section: {str(e)}", e) from e

    def unlink_section(self, link_id: str) -> bool:
        """
        Remove a link from a section.

        Args:
            link_id: Link ID

        Returns:
            True if link was deleted, False if not found

        Raises:
            ValidationError: If link_id is invalid
            DatabaseError: If database operation fails
        """
        self.validator.validate_id(link_id)

        try:
            deleted = self.link_repo.delete(link_id)
            if deleted:
                self.session.commit()
            return deleted

        except ValidationError:
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to unlink section: {str(e)}", e) from e

    def link_document(
        self,
        document_id: str,
        link_type: str,
        link_target: str,
        link_metadata: dict[str, Any] | None = None,
        link_id: str | None = None,
    ) -> Link:
        """
        Link a document to an external resource (To-Do-Rama, Bucket-O-Facts, or GitHub).

        Args:
            document_id: Document ID (required)
            link_type: Link type ('todo-rama', 'bucket-o-facts', or 'github')
            link_target: Link target (URI or identifier)
            link_metadata: Optional link metadata (JSON structure)
            link_id: Optional link ID. If not provided, generates a UUID.

        Returns:
            Created link with ID

        Raises:
            ValidationError: If document_id, link_type, or link_target is invalid
            NotFoundError: If document is not found
            DuplicateError: If link with same ID already exists or duplicate link
            DatabaseError: If database operation fails
        """
        # Validate document_id
        self.validator.validate_id(document_id)

        # Verify document exists
        document = self.document_repo.get_by_id(document_id)
        if document is None:
            raise NotFoundError("Document", document_id)

        # Validate link_type
        self.validator.validate_link_type(link_type)

        # Validate link_target format
        self.validator.validate_link_target(link_target)
        self.validator.validate_link_target_format(link_type, link_target)

        # Check for duplicate link (same document + link_type + link_target)
        existing_links = self.link_repo.get_by_document_id(document_id)
        for existing in existing_links:
            if existing.link_type == link_type and existing.link_target == link_target:
                raise DuplicateError(
                    "Link",
                    "document_id+link_type+link_target",
                    f"{document_id}+{link_type}+{link_target}",
                )

        # Validate metadata
        if link_metadata is not None:
            self.validator.validate_metadata(link_metadata)

        # Generate ID if not provided
        if link_id is None:
            link_id = str(uuid.uuid4())
        else:
            self.validator.validate_id(link_id)

        # Check for duplicate ID
        existing = self.link_repo.get_by_id(link_id)
        if existing is not None:
            raise DuplicateError("Link", "id", link_id)

        try:
            # Create link
            link = Link(
                id=link_id,
                section_id=None,
                document_id=document_id,
                link_type=link_type,
                link_target=link_target,
                link_metadata=link_metadata or {},
            )
            self.link_repo.create(link)
            self.session.commit()
            return link

        except (DuplicateError, ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to link document: {str(e)}", e) from e

    def unlink_document(self, link_id: str) -> bool:
        """
        Remove a link from a document.

        Args:
            link_id: Link ID

        Returns:
            True if link was deleted, False if not found

        Raises:
            ValidationError: If link_id is invalid
            DatabaseError: If database operation fails
        """
        self.validator.validate_id(link_id)

        try:
            deleted = self.link_repo.delete(link_id)
            if deleted:
                self.session.commit()
            return deleted

        except ValidationError:
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to unlink document: {str(e)}", e) from e

    def get_section_links(self, section_id: str) -> list[Link]:
        """
        Get all links for a section.

        Args:
            section_id: Section ID

        Returns:
            List of links

        Raises:
            ValidationError: If section_id is invalid
            DatabaseError: If database operation fails
        """
        self.validator.validate_id(section_id)

        try:
            return self.link_repo.get_by_section_id(section_id)

        except ValidationError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get section links: {str(e)}", e) from e

    def get_sections_by_link(
        self, link_type: str, link_target: str
    ) -> list[dict[str, Any]]:
        """
        Find all sections linked to a specific task/fact/GitHub resource.

        Args:
            link_type: Link type ('todo-rama', 'bucket-o-facts', or 'github')
            link_target: Link target (URI or identifier)

        Returns:
            List of section summaries with link information

        Raises:
            ValidationError: If link_type or link_target is invalid
            DatabaseError: If database operation fails
        """
        self.validator.validate_link_type(link_type)
        self.validator.validate_link_target(link_target)

        try:
            links = self.link_repo.get_by_link_target(link_type, link_target)
            sections = []
            for link in links:
                if link.section_id:
                    section = self.section_repo.get_by_id(link.section_id)
                    if section:
                        sections.append(
                            {
                                "section_id": section.id,
                                "heading": section.heading,
                                "document_id": section.document_id,
                                "link_id": link.id,
                                "link_target": link.link_target,
                                "link_metadata": link.link_metadata,
                            }
                        )
            return sections

        except ValidationError:
            raise
        except Exception as e:
            raise DatabaseError(
                f"Failed to get sections by link: {str(e)}", e
            ) from e

    def get_document_links(self, document_id: str) -> list[Link]:
        """
        Get all links for a document.

        Args:
            document_id: Document ID

        Returns:
            List of links

        Raises:
            ValidationError: If document_id is invalid
            DatabaseError: If database operation fails
        """
        self.validator.validate_id(document_id)

        try:
            return self.link_repo.get_by_document_id(document_id)

        except ValidationError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get document links: {str(e)}", e) from e

    def get_links_by_type(
        self, link_type: str, limit: int = 100
    ) -> list[Link]:
        """
        Get all links of a specific type.

        Args:
            link_type: Link type ('todo-rama', 'bucket-o-facts', or 'github')
            limit: Maximum number of links to return (default: 100)

        Returns:
            List of links

        Raises:
            ValidationError: If link_type is invalid
            DatabaseError: If database operation fails
        """
        self.validator.validate_link_type(link_type)

        try:
            return self.link_repo.get_by_link_type(link_type, limit=limit)

        except ValidationError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get links by type: {str(e)}", e) from e

    def get_documents_by_link(
        self, link_type: str, link_target: str
    ) -> list[dict[str, Any]]:
        """
        Find all documents linked to a specific task/fact/GitHub resource.

        Args:
            link_type: Link type ('todo-rama', 'bucket-o-facts', or 'github')
            link_target: Link target (URI or identifier)

        Returns:
            List of document summaries with link information

        Raises:
            ValidationError: If link_type or link_target is invalid
            DatabaseError: If database operation fails
        """
        self.validator.validate_link_type(link_type)
        self.validator.validate_link_target(link_target)

        try:
            links = self.link_repo.get_by_link_target(link_type, link_target)
            documents = []
            for link in links:
                if link.document_id and not link.section_id:
                    # Only document-level links (not section-level)
                    document = self.document_repo.get_by_id(link.document_id)
                    if document:
                        documents.append(
                            {
                                "document_id": document.id,
                                "title": document.title,
                                "link_id": link.id,
                                "link_metadata": link.link_metadata,
                            }
                        )
            return documents

        except ValidationError:
            raise
        except Exception as e:
            raise DatabaseError(
                f"Failed to get documents by link: {str(e)}", e
            ) from e

    def update_link_metadata(
        self, link_id: str, link_metadata: dict[str, Any]
    ) -> Link:
        """
        Update link metadata.

        Args:
            link_id: Link ID
            link_metadata: New link metadata (JSON structure)

        Returns:
            Updated link

        Raises:
            ValidationError: If link_id is invalid or metadata is invalid
            NotFoundError: If link is not found
            DatabaseError: If database operation fails
        """
        self.validator.validate_id(link_id)
        self.validator.validate_metadata(link_metadata)

        try:
            link = self.link_repo.get_by_id(link_id)
            if link is None:
                raise NotFoundError("Link", link_id)

            link.link_metadata = link_metadata
            self.link_repo.update(link)
            self.session.commit()
            return link

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(
                f"Failed to update link metadata: {str(e)}", e
            ) from e

    def generate_link_report(
        self, document_id: str | None = None, link_type: str | None = None
    ) -> dict[str, Any]:
        """
        Generate a comprehensive link report.

        Args:
            document_id: Optional document ID to filter by
            link_type: Optional link type to filter by

        Returns:
            Dictionary containing link statistics and breakdown

        Raises:
            ValidationError: If document_id or link_type is invalid
            DatabaseError: If database operation fails
        """
        return self.reporter.generate_link_report(document_id, link_type)
