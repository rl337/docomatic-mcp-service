"""Shared pytest fixtures and test utilities for Doc-O-Matic tests."""

import os
import tempfile
import uuid
from typing import Generator

import pytest

from docomatic.models.document import Document
from docomatic.models.link import Link
from docomatic.models.section import Section
from docomatic.services.document_service import DocumentService
from docomatic.services.link_service import LinkService
from docomatic.services.section_service import SectionService
from docomatic.storage.database import Database, reset_db


@pytest.fixture(scope="function")
def temp_db() -> Generator[Database, None, None]:
    """
    Create a temporary SQLite database for testing.
    
    Yields:
        Database instance with tables created
    """
    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Reset global database instance
    reset_db()
    
    # Create database
    database = Database(f"sqlite:///{db_path}")
    database.create_tables()
    
    yield database
    
    # Cleanup
    database.drop_tables()
    reset_db()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def db_session(temp_db):
    """Get a database session from temp_db."""
    with temp_db.session() as session:
        yield session


@pytest.fixture
def document_service(temp_db):
    """Create a document service instance."""
    with temp_db.session() as session:
        yield DocumentService(session)


@pytest.fixture
def section_service(temp_db):
    """Create a section service instance."""
    with temp_db.session() as session:
        yield SectionService(session)


@pytest.fixture
def link_service(temp_db):
    """Create a link service instance."""
    with temp_db.session() as session:
        yield LinkService(session)


@pytest.fixture
def sample_document(temp_db):
    """Create a sample document for testing."""
    with temp_db.session() as session:
        service = DocumentService(session)
        doc = service.create_document(
            title="Sample Document",
            metadata={"author": "test", "version": "1.0"}
        )
        yield doc


@pytest.fixture
def sample_document_with_sections(temp_db):
    """Create a sample document with sections for testing."""
    with temp_db.session() as session:
        doc_service = DocumentService(session)
        section_service = SectionService(session)
        
        doc = doc_service.create_document(title="Sample Document")
        
        # Create top-level sections
        section1 = section_service.create_section(
            document_id=doc.id,
            heading="Introduction",
            body="This is the introduction section."
        )
        section2 = section_service.create_section(
            document_id=doc.id,
            heading="Main Content",
            body="This is the main content section."
        )
        
        # Create nested section
        section3 = section_service.create_section(
            document_id=doc.id,
            heading="Subsection",
            body="This is a subsection.",
            parent_section_id=section1.id
        )
        
        yield doc, [section1, section2, section3]


@pytest.fixture
def sample_link(temp_db, sample_document_with_sections):
    """Create a sample link for testing."""
    doc, sections = sample_document_with_sections
    with temp_db.session() as session:
        link_service = LinkService(session)
        link = link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target="todo-rama://task/123",
            link_metadata={"title": "Test Task"}
        )
        yield link


class TestDataGenerator:
    """Utility class for generating test data."""
    
    @staticmethod
    def generate_document_id() -> str:
        """Generate a unique document ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_section_id() -> str:
        """Generate a unique section ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_link_id() -> str:
        """Generate a unique link ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def create_document_data(title: str = None, metadata: dict = None) -> dict:
        """Create document data dictionary."""
        return {
            "id": TestDataGenerator.generate_document_id(),
            "title": title or f"Test Document {uuid.uuid4().hex[:8]}",
            "metadata": metadata or {}
        }
    
    @staticmethod
    def create_section_data(
        document_id: str,
        heading: str = None,
        body: str = None,
        parent_section_id: str = None,
        order_index: int = 0,
        metadata: dict = None
    ) -> dict:
        """Create section data dictionary."""
        return {
            "id": TestDataGenerator.generate_section_id(),
            "document_id": document_id,
            "heading": heading or f"Test Section {uuid.uuid4().hex[:8]}",
            "body": body or f"Test content for section {uuid.uuid4().hex[:8]}",
            "parent_section_id": parent_section_id,
            "order_index": order_index,
            "metadata": metadata or {}
        }
    
    @staticmethod
    def create_link_data(
        section_id: str,
        document_id: str,
        link_type: str = "todo-rama",
        link_target: str = None,
        link_metadata: dict = None
    ) -> dict:
        """Create link data dictionary."""
        if link_target is None:
            if link_type == "todo-rama":
                link_target = f"todo-rama://task/{uuid.uuid4().hex[:8]}"
            elif link_type == "bucket-o-facts":
                link_target = f"bucket-o-facts://fact/{uuid.uuid4().hex[:8]}"
            elif link_type == "github":
                link_target = f"github://repo/{uuid.uuid4().hex[:8]}"
            else:
                link_target = f"test://target/{uuid.uuid4().hex[:8]}"
        
        return {
            "id": TestDataGenerator.generate_link_id(),
            "section_id": section_id,
            "document_id": document_id,
            "link_type": link_type,
            "link_target": link_target,
            "link_metadata": link_metadata or {}
        }
    
    @staticmethod
    def create_hierarchical_sections(
        document_id: str,
        depth: int = 3,
        width: int = 2
    ) -> list[dict]:
        """
        Create hierarchical section data.
        
        Args:
            document_id: Document ID
            depth: Maximum depth of hierarchy
            width: Number of children per parent
        
        Returns:
            List of section data dictionaries in creation order
        """
        sections = []
        order_index = 0
        
        def create_level(parent_id: str | None, current_depth: int):
            nonlocal order_index
            if current_depth > depth:
                return
            
            for i in range(width):
                section_data = TestDataGenerator.create_section_data(
                    document_id=document_id,
                    heading=f"Level {current_depth} Section {i+1}",
                    body=f"Content for level {current_depth} section {i+1}",
                    parent_section_id=parent_id,
                    order_index=order_index,
                    metadata={"level": current_depth, "index": i}
                )
                sections.append(section_data)
                section_id = section_data["id"]
                order_index += 1
                
                # Recursively create children
                create_level(section_id, current_depth + 1)
        
        create_level(None, 1)
        return sections


class AssertionHelpers:
    """Helper functions for test assertions."""
    
    @staticmethod
    def assert_document_equal(doc1: Document, doc2: Document):
        """Assert two documents are equal."""
        assert doc1.id == doc2.id
        assert doc1.title == doc2.title
        assert doc1.metadata == doc2.metadata
    
    @staticmethod
    def assert_section_equal(section1: Section, section2: Section):
        """Assert two sections are equal."""
        assert section1.id == section2.id
        assert section1.document_id == section2.document_id
        assert section1.heading == section2.heading
        assert section1.body == section2.body
        assert section1.parent_section_id == section2.parent_section_id
        assert section1.order_index == section2.order_index
        assert section1.metadata == section2.metadata
    
    @staticmethod
    def assert_link_equal(link1: Link, link2: Link):
        """Assert two links are equal."""
        assert link1.id == link2.id
        assert link1.section_id == link2.section_id
        assert link1.document_id == link2.document_id
        assert link1.link_type == link2.link_type
        assert link1.link_target == link2.link_target
        assert link1.link_metadata == link2.link_metadata
    
    @staticmethod
    def assert_section_hierarchy(sections: list[Section], expected_structure: dict):
        """
        Assert section hierarchy matches expected structure.
        
        Args:
            sections: List of sections (tree structure)
            expected_structure: Dict mapping section IDs to expected child IDs
        """
        section_dict = {s.id: s for s in sections}
        
        for parent_id, expected_children in expected_structure.items():
            parent = section_dict.get(parent_id)
            assert parent is not None, f"Parent section {parent_id} not found"
            
            actual_children = {c.id for c in parent.child_sections}
            expected_children_set = set(expected_children)
            assert actual_children == expected_children_set, \
                f"Children mismatch for {parent_id}: expected {expected_children_set}, got {actual_children}"


# Make utilities available as fixtures
@pytest.fixture
def test_data_generator():
    """Provide TestDataGenerator instance."""
    return TestDataGenerator


@pytest.fixture
def assertion_helpers():
    """Provide AssertionHelpers instance."""
    return AssertionHelpers
