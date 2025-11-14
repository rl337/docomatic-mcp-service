"""Repository pattern implementation for data access layer."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session, joinedload

from docomatic.config import get_settings
from docomatic.models.document import Document
from docomatic.models.link import Link
from docomatic.models.section import Section


class DocumentRepository:
    """Repository for document operations."""

    def __init__(self, session: Session):
        """Initialize repository with a database session."""
        self.session = session

    def create(self, document: Document) -> Document:
        """Create a new document."""
        self.session.add(document)
        self.session.flush()
        return document

    def get_by_id(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self.session.get(Document, document_id)

    def get_by_id_with_sections(
        self, document_id: str, include_children: bool = True
    ) -> Optional[Document]:
        """Get document by ID with all sections loaded."""
        stmt = select(Document).where(Document.id == document_id)
        if include_children:
            stmt = stmt.options(joinedload(Document.sections))
        return self.session.scalar(stmt)

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Document]:
        """Get all documents with pagination."""
        stmt = select(Document).limit(limit).offset(offset).order_by(Document.created_at.desc())
        return list(self.session.scalars(stmt))

    def list(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters: Any
    ) -> list[Document]:
        """List documents with optional filters (standardized method name).
        
        This method provides a standardized interface consistent with other MCP services.
        For backward compatibility, get_all() is still available.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            **filters: Optional filter parameters (currently unused, reserved for future use)
            
        Returns:
            List of documents
        """
        # For now, delegate to get_all() - filters can be added later if needed
        return self.get_all(limit=limit, offset=offset)

    def count(self, **filters: Any) -> int:
        """Count documents matching optional filters.
        
        Args:
            **filters: Optional filter parameters (currently unused, reserved for future use)
            
        Returns:
            Count of documents
        """
        query = select(func.count(Document.id))
        # Filters can be added here if needed in the future
        return self.session.scalar(query) or 0

    def search_by_title(self, title_pattern: str, limit: int = 100) -> list[Document]:
        """Search documents by title pattern."""
        stmt = (
            select(Document)
            .where(Document.title.ilike(f"%{title_pattern}%"))
            .limit(limit)
            .order_by(Document.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def update(self, document: Document) -> Document:
        """Update an existing document."""
        self.session.flush()
        return document

    def update_by_id(
        self,
        document_id: str,
        **kwargs: Any
    ) -> Optional[Document]:
        """Update a document by ID with field updates (standardized method).
        
        This method provides a standardized interface consistent with other MCP services.
        For backward compatibility, update(document) is still available.
        
        Args:
            document_id: Document identifier
            **kwargs: Fields to update (title, metadata, etc.)
            
        Returns:
            Updated document if found, None otherwise
        """
        document = self.get_by_id(document_id)
        if document is None:
            return None
        
        for key, value in kwargs.items():
            if hasattr(document, key):
                setattr(document, key, value)
        
        self.session.flush()
        return document

    def delete(self, document_id: str) -> bool:
        """Delete a document by ID."""
        document = self.get_by_id(document_id)
        if document:
            self.session.delete(document)
            return True
        return False


class SectionRepository:
    """Repository for section operations with hierarchical query support."""

    def __init__(self, session: Session):
        """Initialize repository with a database session."""
        self.session = session

    def create(self, section: Section) -> Section:
        """Create a new section."""
        self.session.add(section)
        self.session.flush()
        return section

    def get_by_id(self, section_id: str) -> Optional[Section]:
        """Get section by ID."""
        return self.session.get(Section, section_id)

    def get_by_id_with_children(self, section_id: str) -> Optional[Section]:
        """Get section by ID with all children loaded."""
        stmt = select(Section).where(Section.id == section_id).options(
            joinedload(Section.child_sections)
        )
        return self.session.scalar(stmt)

    def get_by_document_id(
        self, document_id: str, flat: bool = False
    ) -> list[Section]:
        """
        Get all sections for a document.

        Args:
            document_id: Document ID
            flat: If True, return flat list. If False, return tree structure (top-level only).

        Returns:
            List of sections
        """
        if flat:
            stmt = (
                select(Section)
                .where(Section.document_id == document_id)
                .order_by(Section.order_index)
            )
            return list(self.session.scalars(stmt))
        else:
            # Return only top-level sections (parent_section_id is NULL)
            stmt = (
                select(Section)
                .where(
                    and_(
                        Section.document_id == document_id,
                        Section.parent_section_id.is_(None),
                    )
                )
                .order_by(Section.order_index)
            )
            return list(self.session.scalars(stmt))

    def get_children(self, parent_section_id: str) -> list[Section]:
        """Get all direct children of a section."""
        stmt = (
            select(Section)
            .where(Section.parent_section_id == parent_section_id)
            .order_by(Section.order_index)
        )
        return list(self.session.scalars(stmt))

    def get_section_tree(self, section_id: str) -> Optional[Section]:
        """
        Get a section with its entire subtree using recursive CTE.

        This uses a recursive query to efficiently load the entire tree.
        """
        # For PostgreSQL, use recursive CTE
        # For SQLite, we'll use a simpler approach with multiple queries
        section = self.get_by_id_with_children(section_id)
        if section:
            # Recursively load children
            self._load_children_recursive(section)
        return section

    def _load_children_recursive(self, section: Section) -> None:
        """Recursively load all children of a section."""
        if section.child_sections:
            for child in section.child_sections:
                # Load children of this child
                child_stmt = select(Section).where(
                    Section.parent_section_id == child.id
                )
                child.child_sections = list(self.session.scalars(child_stmt))
                self._load_children_recursive(child)

    def get_section_tree_by_document(self, document_id: str) -> list[Section]:
        """
        Get the complete section tree for a document.

        Returns top-level sections with all descendants loaded.
        """
        top_level = self.get_by_document_id(document_id, flat=False)
        for section in top_level:
            self._load_children_recursive(section)
        return top_level

    def search_by_heading(
        self, heading_pattern: str, document_id: Optional[str] = None, limit: int = 100
    ) -> list[Section]:
        """Search sections by heading pattern."""
        conditions = [Section.heading.ilike(f"%{heading_pattern}%")]
        if document_id:
            conditions.append(Section.document_id == document_id)

        stmt = (
            select(Section)
            .where(and_(*conditions))
            .limit(limit)
            .order_by(Section.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def full_text_search(
        self, query: str, document_id: Optional[str] = None, limit: int = 100
    ) -> list[Section]:
        """
        Full-text search on section heading and body.

        Uses PostgreSQL tsvector/tsquery for efficient search when available.
        Falls back to LIKE queries for SQLite.
        """
        # Check if using PostgreSQL
        is_postgresql = get_settings().is_postgresql()

        if is_postgresql:
            # Use PostgreSQL full-text search with tsvector/tsquery
            # Escape special characters in query for tsquery
            escaped_query = query.replace("'", "''").replace(":", "\\:")
            tsquery = func.plainto_tsquery("english", escaped_query)

            # Build tsvector from heading and body
            search_vector = func.to_tsvector("english", Section.heading + " " + Section.body)

            # Calculate relevance score (ts_rank)
            relevance = func.ts_rank(search_vector, tsquery)

            conditions = [search_vector.op("@@")(tsquery)]
            if document_id:
                conditions.append(Section.document_id == document_id)

            stmt = (
                select(Section, relevance.label("relevance"))
                .where(and_(*conditions))
                .order_by(relevance.desc(), Section.created_at.desc())
                .limit(limit)
            )

            # Execute and extract sections (PostgreSQL returns tuples with relevance)
            results = self.session.execute(stmt).all()
            return [section for section, _ in results]
        else:
            # SQLite fallback: use LIKE queries
            conditions = [
                or_(
                    Section.heading.ilike(f"%{query}%"),
                    Section.body.ilike(f"%{query}%"),
                )
            ]
            if document_id:
                conditions.append(Section.document_id == document_id)

            stmt = (
                select(Section)
                .where(and_(*conditions))
                .limit(limit)
                .order_by(Section.created_at.desc())
            )
            return list(self.session.scalars(stmt))

    def update(self, section: Section) -> Section:
        """Update an existing section."""
        self.session.flush()
        return section

    def update_by_id(
        self,
        section_id: str,
        **kwargs: Any
    ) -> Optional[Section]:
        """Update a section by ID with field updates (standardized method).
        
        This method provides a standardized interface consistent with other MCP services.
        For backward compatibility, update(section) is still available.
        
        Args:
            section_id: Section identifier
            **kwargs: Fields to update (heading, body, order_index, etc.)
            
        Returns:
            Updated section if found, None otherwise
        """
        section = self.get_by_id(section_id)
        if section is None:
            return None
        
        for key, value in kwargs.items():
            if hasattr(section, key):
                setattr(section, key, value)
        
        self.session.flush()
        return section

    def list(
        self,
        document_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        **filters: Any
    ) -> list[Section]:
        """List sections with optional filters (standardized method name).
        
        This method provides a standardized interface consistent with other MCP services.
        
        Args:
            document_id: Optional document ID filter
            limit: Maximum number of results
            offset: Number of results to skip
            **filters: Additional filter parameters (currently unused, reserved for future use)
            
        Returns:
            List of sections
        """
        query = select(Section)
        
        if document_id:
            query = query.where(Section.document_id == document_id)
        
        query = query.limit(limit).offset(offset).order_by(Section.created_at.desc())
        return list(self.session.scalars(query))

    def count(
        self,
        document_id: Optional[str] = None,
        **filters: Any
    ) -> int:
        """Count sections matching optional filters.
        
        Args:
            document_id: Optional document ID filter
            **filters: Additional filter parameters (currently unused, reserved for future use)
            
        Returns:
            Count of sections
        """
        query = select(func.count(Section.id))
        
        if document_id:
            query = query.where(Section.document_id == document_id)
        
        return self.session.scalar(query) or 0

    def delete(self, section_id: str) -> bool:
        """Delete a section by ID (cascades to children)."""
        section = self.get_by_id(section_id)
        if section:
            self.session.delete(section)
            return True
        return False

    def get_path_to_root(self, section_id: str) -> list[Section]:
        """
        Get the path from a section to the root (document level).

        Returns sections in order from root to the specified section.
        """
        path = []
        current = self.get_by_id(section_id)
        while current:
            path.insert(0, current)
            if current.parent_section_id:
                current = self.get_by_id(current.parent_section_id)
            else:
                break
        return path


class LinkRepository:
    """Repository for link operations."""

    def __init__(self, session: Session):
        """Initialize repository with a database session."""
        self.session = session

    def create(self, link: Link) -> Link:
        """Create a new link."""
        self.session.add(link)
        self.session.flush()
        return link

    def get_by_id(self, link_id: str) -> Optional[Link]:
        """Get link by ID."""
        return self.session.get(Link, link_id)

    def get_by_section_id(self, section_id: str) -> list[Link]:
        """Get all links for a section."""
        stmt = select(Link).where(Link.section_id == section_id)
        return list(self.session.scalars(stmt))

    def get_by_document_id(self, document_id: str) -> list[Link]:
        """Get all links for a document."""
        stmt = select(Link).where(Link.document_id == document_id)
        return list(self.session.scalars(stmt))

    def get_by_link_type(
        self, link_type: str, limit: int = 100
    ) -> list[Link]:
        """Get all links of a specific type."""
        stmt = (
            select(Link)
            .where(Link.link_type == link_type)
            .limit(limit)
            .order_by(Link.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def get_by_link_target(
        self, link_type: str, link_target: str
    ) -> list[Link]:
        """Get links by type and target (e.g., all links to a specific task)."""
        stmt = select(Link).where(
            and_(Link.link_type == link_type, Link.link_target == link_target)
        )
        return list(self.session.scalars(stmt))

    def update(self, link: Link) -> Link:
        """Update an existing link."""
        self.session.flush()
        return link

    def update_by_id(
        self,
        link_id: str,
        **kwargs: Any
    ) -> Optional[Link]:
        """Update a link by ID with field updates (standardized method).
        
        This method provides a standardized interface consistent with other MCP services.
        For backward compatibility, update(link) is still available.
        
        Args:
            link_id: Link identifier
            **kwargs: Fields to update (link_type, link_target, metadata, etc.)
            
        Returns:
            Updated link if found, None otherwise
        """
        link = self.get_by_id(link_id)
        if link is None:
            return None
        
        for key, value in kwargs.items():
            if hasattr(link, key):
                setattr(link, key, value)
        
        self.session.flush()
        return link

    def list(
        self,
        section_id: Optional[str] = None,
        document_id: Optional[str] = None,
        link_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        **filters: Any
    ) -> list[Link]:
        """List links with optional filters (standardized method name).
        
        This method provides a standardized interface consistent with other MCP services.
        
        Args:
            section_id: Optional section ID filter
            document_id: Optional document ID filter
            link_type: Optional link type filter
            limit: Maximum number of results
            offset: Number of results to skip
            **filters: Additional filter parameters (currently unused, reserved for future use)
            
        Returns:
            List of links
        """
        query = select(Link)
        
        if section_id:
            query = query.where(Link.section_id == section_id)
        if document_id:
            query = query.where(Link.document_id == document_id)
        if link_type:
            query = query.where(Link.link_type == link_type)
        
        query = query.limit(limit).offset(offset).order_by(Link.created_at.desc())
        return list(self.session.scalars(query))

    def count(
        self,
        section_id: Optional[str] = None,
        document_id: Optional[str] = None,
        link_type: Optional[str] = None,
        **filters: Any
    ) -> int:
        """Count links matching optional filters.
        
        Args:
            section_id: Optional section ID filter
            document_id: Optional document ID filter
            link_type: Optional link type filter
            **filters: Additional filter parameters (currently unused, reserved for future use)
            
        Returns:
            Count of links
        """
        query = select(func.count(Link.id))
        
        if section_id:
            query = query.where(Link.section_id == section_id)
        if document_id:
            query = query.where(Link.document_id == document_id)
        if link_type:
            query = query.where(Link.link_type == link_type)
        
        return self.session.scalar(query) or 0

    def delete(self, link_id: str) -> bool:
        """Delete a link by ID."""
        link = self.get_by_id(link_id)
        if link:
            self.session.delete(link)
            return True
        return False
