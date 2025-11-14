"""Comprehensive tests for document service CRUD operations."""

import os
import tempfile
import uuid

import pytest

pytestmark = pytest.mark.unit

from docomatic.exceptions import (
    DatabaseError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from docomatic.models.document import Document
from docomatic.models.section import Section
from docomatic.services.document_service import DocumentService
from docomatic.storage.database import Database


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    database = Database(f"sqlite:///{db_path}")
    database.create_tables()

    yield database

    # Cleanup
    database.drop_tables()
    os.unlink(db_path)


@pytest.fixture
def service(db):
    """Create a document service instance."""
    with db.session() as session:
        yield DocumentService(session)


class TestCreateDocument:
    """Tests for document creation."""

    def test_create_document_basic(self, service):
        """Test creating a document with minimal required fields."""
        doc = service.create_document(title="Test Document")
        assert doc.id is not None
        assert doc.title == "Test Document"
        assert doc.metadata == {}

    def test_create_document_with_metadata(self, service):
        """Test creating a document with metadata."""
        metadata = {"author": "test", "version": "1.0"}
        doc = service.create_document(title="Test Document", metadata=metadata)
        assert doc.metadata == metadata

    def test_create_document_with_custom_id(self, service):
        """Test creating a document with custom ID."""
        custom_id = str(uuid.uuid4())
        doc = service.create_document(title="Test Document", document_id=custom_id)
        assert doc.id == custom_id

    def test_create_document_with_initial_sections(self, service):
        """Test creating a document with initial sections."""
        initial_sections = [
            {"heading": "Section 1", "body": "Content 1", "order_index": 0},
            {"heading": "Section 2", "body": "Content 2", "order_index": 1},
        ]
        doc = service.create_document(
            title="Test Document", initial_sections=initial_sections
        )
        assert doc.id is not None

        # Verify sections were created
        sections = service.section_repo.get_by_document_id(doc.id, flat=True)
        assert len(sections) == 2
        assert sections[0].heading == "Section 1"
        assert sections[1].heading == "Section 2"

    def test_create_document_with_nested_sections(self, service):
        """Test creating a document with nested sections."""
        # Create document with parent section first
        doc = service.create_document(
            title="Test Document",
            initial_sections=[
                {"heading": "Parent", "body": "Parent content", "order_index": 0}
            ],
        )

        # Get parent section
        parent_sections = service.section_repo.get_by_document_id(doc.id, flat=True)
        parent_id = parent_sections[0].id

        # Create child section
        child_section = Section(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            parent_section_id=parent_id,
            heading="Child",
            body="Child content",
            order_index=0,
        )
        service.section_repo.create(child_section)
        service.session.commit()

        # Verify hierarchy
        tree = service.section_repo.get_section_tree_by_document(doc.id)
        assert len(tree) == 1
        assert len(tree[0].child_sections) == 1
        assert tree[0].child_sections[0].heading == "Child"

    def test_create_document_duplicate_id(self, service):
        """Test creating a document with duplicate ID raises error."""
        doc_id = str(uuid.uuid4())
        service.create_document(title="First Document", document_id=doc_id)

        with pytest.raises(DuplicateError) as exc_info:
            service.create_document(title="Second Document", document_id=doc_id)
        assert "already exists" in str(exc_info.value)

    def test_create_document_empty_title(self, service):
        """Test creating a document with empty title raises error."""
        with pytest.raises(ValidationError) as exc_info:
            service.create_document(title="")
        assert "Title is required" in str(exc_info.value)

    def test_create_document_whitespace_title(self, service):
        """Test creating a document with whitespace-only title raises error."""
        with pytest.raises(ValidationError) as exc_info:
            service.create_document(title="   ")
        assert "Title is required" in str(exc_info.value)

    def test_create_document_title_too_long(self, service):
        """Test creating a document with title exceeding max length raises error."""
        long_title = "a" * 501
        with pytest.raises(ValidationError) as exc_info:
            service.create_document(title=long_title)
        assert "at most 500 characters" in str(exc_info.value)

    def test_create_document_invalid_metadata(self, service):
        """Test creating a document with invalid metadata raises error."""
        with pytest.raises(ValidationError) as exc_info:
            service.create_document(title="Test", metadata="not a dict")  # type: ignore
        assert "Metadata must be a dictionary" in str(exc_info.value)

    def test_create_document_invalid_id(self, service):
        """Test creating a document with invalid ID raises error."""
        with pytest.raises(ValidationError) as exc_info:
            service.create_document(title="Test", document_id="")
        assert "Document ID cannot be empty" in str(exc_info.value)


class TestGetDocument:
    """Tests for document retrieval."""

    def test_get_document_by_id(self, service):
        """Test getting a document by ID."""
        doc = service.create_document(title="Test Document")
        retrieved = service.get_document(doc.id)
        assert retrieved.id == doc.id
        assert retrieved.title == doc.title

    def test_get_document_with_sections(self, service):
        """Test getting a document with sections tree."""
        initial_sections = [
            {"heading": "Section 1", "body": "Content 1", "order_index": 0}
        ]
        doc = service.create_document(
            title="Test Document", initial_sections=initial_sections
        )

        retrieved = service.get_document(doc.id, include_sections=True)
        assert len(retrieved.sections) == 1
        assert retrieved.sections[0].heading == "Section 1"

    def test_get_document_with_links(self, service):
        """Test getting a document with links."""
        doc = service.create_document(title="Test Document")

        # Create a link (using repository directly for test)
        from docomatic.models.link import Link

        link = Link(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            link_type="todo-rama",
            link_target="task-123",
        )
        service.link_repo.create(link)
        service.session.commit()

        retrieved = service.get_document(doc.id, include_links=True)
        assert len(retrieved.links) == 1
        assert retrieved.links[0].link_type == "todo-rama"

    def test_get_document_not_found(self, service):
        """Test getting a non-existent document raises error."""
        with pytest.raises(NotFoundError) as exc_info:
            service.get_document("non-existent-id")
        assert "not found" in str(exc_info.value)

    def test_get_document_invalid_id(self, service):
        """Test getting a document with invalid ID raises error."""
        with pytest.raises(ValidationError):
            service.get_document("")


class TestUpdateDocument:
    """Tests for document updates."""

    def test_update_document_title(self, service):
        """Test updating document title."""
        doc = service.create_document(title="Original Title")
        updated = service.update_document(doc.id, title="Updated Title")
        assert updated.title == "Updated Title"

    def test_update_document_metadata(self, service):
        """Test updating document metadata."""
        doc = service.create_document(title="Test", metadata={"key": "value"})
        new_metadata = {"key": "new_value", "new_key": "new_value"}
        updated = service.update_document(doc.id, metadata=new_metadata)
        assert updated.metadata == new_metadata

    def test_update_document_both_fields(self, service):
        """Test updating both title and metadata."""
        doc = service.create_document(title="Original", metadata={"old": "value"})
        updated = service.update_document(
            doc.id, title="New Title", metadata={"new": "value"}
        )
        assert updated.title == "New Title"
        assert updated.metadata == {"new": "value"}

    def test_update_document_not_found(self, service):
        """Test updating a non-existent document raises error."""
        with pytest.raises(NotFoundError):
            service.update_document("non-existent-id", title="New Title")

    def test_update_document_empty_title(self, service):
        """Test updating document with empty title raises error."""
        doc = service.create_document(title="Test")
        with pytest.raises(ValidationError):
            service.update_document(doc.id, title="")

    def test_update_document_invalid_metadata(self, service):
        """Test updating document with invalid metadata raises error."""
        doc = service.create_document(title="Test")
        with pytest.raises(ValidationError):
            service.update_document(doc.id, metadata="not a dict")  # type: ignore


class TestDeleteDocument:
    """Tests for document deletion."""

    def test_delete_document(self, service):
        """Test deleting a document."""
        doc = service.create_document(title="Test Document")
        result = service.delete_document(doc.id)
        assert result is True

        # Verify document is deleted
        with pytest.raises(NotFoundError):
            service.get_document(doc.id)

    def test_delete_document_cascades_to_sections(self, service):
        """Test that deleting a document cascades to sections."""
        doc = service.create_document(
            title="Test Document",
            initial_sections=[{"heading": "Section", "body": "Content", "order_index": 0}],
        )

        # Verify section exists
        sections = service.section_repo.get_by_document_id(doc.id, flat=True)
        assert len(sections) == 1

        # Delete document
        service.delete_document(doc.id)

        # Verify section is also deleted
        sections = service.section_repo.get_by_document_id(doc.id, flat=True)
        assert len(sections) == 0

    def test_delete_document_cascades_to_links(self, service):
        """Test that deleting a document cascades to links."""
        doc = service.create_document(title="Test Document")

        # Create a link
        from docomatic.models.link import Link

        link = Link(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            link_type="todo-rama",
            link_target="task-123",
        )
        service.link_repo.create(link)
        service.session.commit()

        # Verify link exists
        links = service.link_repo.get_by_document_id(doc.id)
        assert len(links) == 1

        # Delete document
        service.delete_document(doc.id)

        # Verify link is also deleted
        links = service.link_repo.get_by_document_id(doc.id)
        assert len(links) == 0

    def test_delete_document_not_found(self, service):
        """Test deleting a non-existent document returns False."""
        result = service.delete_document("non-existent-id")
        assert result is False

    def test_delete_document_soft_delete_not_implemented(self, service):
        """Test that soft delete raises NotImplementedError."""
        doc = service.create_document(title="Test")
        with pytest.raises(NotImplementedError):
            service.delete_document(doc.id, soft_delete=True)


class TestListDocuments:
    """Tests for document listing."""

    def test_list_documents_empty(self, service):
        """Test listing documents when none exist."""
        documents = service.list_documents()
        assert documents == []

    def test_list_documents_basic(self, service):
        """Test listing all documents."""
        doc1 = service.create_document(title="Document 1")
        doc2 = service.create_document(title="Document 2")

        documents = service.list_documents()
        assert len(documents) == 2

        # Verify summaries
        titles = {d["title"] for d in documents}
        assert "Document 1" in titles
        assert "Document 2" in titles

    def test_list_documents_with_pagination(self, service):
        """Test listing documents with pagination."""
        # Create multiple documents
        for i in range(5):
            service.create_document(title=f"Document {i}")

        # Get first page
        page1 = service.list_documents(limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = service.list_documents(limit=2, offset=2)
        assert len(page2) == 2

        # Verify no overlap
        page1_ids = {d["id"] for d in page1}
        page2_ids = {d["id"] for d in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_list_documents_with_title_filter(self, service):
        """Test listing documents filtered by title pattern."""
        service.create_document(title="Python Guide")
        service.create_document(title="JavaScript Guide")
        service.create_document(title="Python Tutorial")

        documents = service.list_documents(title_pattern="Python")
        assert len(documents) == 2
        assert all("Python" in d["title"] for d in documents)

    def test_list_documents_with_metadata_filter(self, service):
        """Test listing documents filtered by metadata."""
        service.create_document(
            title="Doc 1", metadata={"category": "guide", "language": "python"}
        )
        service.create_document(
            title="Doc 2", metadata={"category": "tutorial", "language": "python"}
        )
        service.create_document(
            title="Doc 3", metadata={"category": "guide", "language": "javascript"}
        )

        # Filter by category
        documents = service.list_documents(metadata_filter={"category": "guide"})
        assert len(documents) == 2
        assert all(
            d["title"] in ["Doc 1", "Doc 3"] for d in documents
        )

    def test_list_documents_includes_section_count(self, service):
        """Test that document summaries include section count."""
        doc = service.create_document(
            title="Test Document",
            initial_sections=[
                {"heading": "Section 1", "body": "Content", "order_index": 0},
                {"heading": "Section 2", "body": "Content", "order_index": 1},
            ],
        )

        documents = service.list_documents()
        assert len(documents) == 1
        assert documents[0]["section_count"] == 2

    def test_list_documents_includes_timestamps(self, service):
        """Test that document summaries include updated_at timestamp."""
        doc = service.create_document(title="Test Document")

        documents = service.list_documents()
        assert len(documents) == 1
        assert documents[0]["updated_at"] is not None

    def test_list_documents_negative_limit(self, service):
        """Test that negative limit raises error."""
        with pytest.raises(ValidationError) as exc_info:
            service.list_documents(limit=-1)
        assert "limit must be non-negative" in str(exc_info.value)

    def test_list_documents_negative_offset(self, service):
        """Test that negative offset raises error."""
        with pytest.raises(ValidationError) as exc_info:
            service.list_documents(offset=-1)
        assert "offset must be non-negative" in str(exc_info.value)
