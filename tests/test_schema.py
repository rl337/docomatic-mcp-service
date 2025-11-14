"""Basic tests for database schema."""

import os
import tempfile
import uuid

import pytest

pytestmark = pytest.mark.unit

from docomatic.models.document import Document
from docomatic.models.link import Link
from docomatic.models.section import Section
from docomatic.storage.database import Database


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    # Use SQLite for testing
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    database = Database(f"sqlite:///{db_path}")
    database.create_tables()

    yield database

    # Cleanup
    database.drop_tables()
    os.unlink(db_path)


def test_create_document(db):
    """Test creating a document."""
    with db.session() as session:
        doc = Document(
            id=str(uuid.uuid4()),
            title="Test Document",
            metadata={"author": "test"},
        )
        session.add(doc)
        session.commit()

        # Verify document was created
        retrieved = session.get(Document, doc.id)
        assert retrieved is not None
        assert retrieved.title == "Test Document"
        assert retrieved.metadata == {"author": "test"}


def test_create_section_hierarchy(db):
    """Test creating sections with parent-child relationships."""
    with db.session() as session:
        # Create document
        doc = Document(
            id=str(uuid.uuid4()),
            title="Test Document",
        )
        session.add(doc)
        session.flush()

        # Create top-level section
        section1 = Section(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            heading="Section 1",
            body="Content 1",
            order_index=0,
        )
        session.add(section1)
        session.flush()

        # Create child section
        section2 = Section(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            parent_section_id=section1.id,
            heading="Subsection 1.1",
            body="Content 1.1",
            order_index=0,
        )
        session.add(section2)
        session.commit()

        # Verify hierarchy
        retrieved = session.get(Section, section2.id)
        assert retrieved is not None
        assert retrieved.parent_section_id == section1.id
        assert retrieved.document_id == doc.id


def test_create_link(db):
    """Test creating a link."""
    with db.session() as session:
        # Create document and section
        doc = Document(id=str(uuid.uuid4()), title="Test Document")
        session.add(doc)
        session.flush()

        section = Section(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            heading="Section",
            body="Content",
            order_index=0,
        )
        session.add(section)
        session.flush()

        # Create link
        link = Link(
            id=str(uuid.uuid4()),
            section_id=section.id,
            link_type="todo-rama",
            link_target="task-123",
            link_metadata={"title": "Test Task"},
        )
        session.add(link)
        session.commit()

        # Verify link
        retrieved = session.get(Link, link.id)
        assert retrieved is not None
        assert retrieved.link_type == "todo-rama"
        assert retrieved.link_target == "task-123"
        assert retrieved.section_id == section.id


def test_cascade_delete(db):
    """Test that deleting a document cascades to sections and links."""
    with db.session() as session:
        # Create document, section, and link
        doc = Document(id=str(uuid.uuid4()), title="Test Document")
        session.add(doc)
        session.flush()

        section = Section(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            heading="Section",
            body="Content",
            order_index=0,
        )
        session.add(section)
        session.flush()

        link = Link(
            id=str(uuid.uuid4()),
            section_id=section.id,
            link_type="todo-rama",
            link_target="task-123",
        )
        session.add(link)
        session.commit()

        # Delete document
        session.delete(doc)
        session.commit()

        # Verify cascade delete
        assert session.get(Section, section.id) is None
        assert session.get(Link, link.id) is None
