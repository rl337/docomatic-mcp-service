"""Comprehensive tests for section service CRUD operations and hierarchical management."""

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
from docomatic.services.section_service import SectionService
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
def doc_service(db):
    """Create a document service instance."""
    with db.session() as session:
        yield DocumentService(session)


@pytest.fixture
def service(db, doc_service):
    """Create a section service instance with a test document."""
    with db.session() as session:
        doc_service = DocumentService(session)
        doc = doc_service.create_document(title="Test Document")
        section_service = SectionService(session)
        yield section_service, doc.id


class TestCreateSection:
    """Tests for section creation."""

    def test_create_section_basic(self, service):
        """Test creating a section with minimal required fields."""
        section_service, doc_id = service
        section = section_service.create_section(
            document_id=doc_id, heading="Test Section", body="Test content"
        )
        assert section.id is not None
        assert section.heading == "Test Section"
        assert section.body == "Test content"
        assert section.document_id == doc_id
        assert section.parent_section_id is None
        assert section.order_index == 0

    def test_create_section_with_metadata(self, service):
        """Test creating a section with metadata."""
        section_service, doc_id = service
        metadata = {"author": "test", "version": "1.0"}
        section = section_service.create_section(
            document_id=doc_id,
            heading="Test Section",
            body="Test content",
            metadata=metadata,
        )
        assert section.metadata == metadata

    def test_create_section_with_custom_id(self, service):
        """Test creating a section with custom ID."""
        section_service, doc_id = service
        custom_id = str(uuid.uuid4())
        section = section_service.create_section(
            document_id=doc_id,
            heading="Test Section",
            body="Test content",
            section_id=custom_id,
        )
        assert section.id == custom_id

    def test_create_section_auto_increment_order(self, service):
        """Test that order_index is auto-incremented when not provided."""
        section_service, doc_id = service
        # Create first section
        section1 = section_service.create_section(
            document_id=doc_id, heading="Section 1", body="Content 1"
        )
        assert section1.order_index == 0

        # Create second section (should auto-increment)
        section2 = section_service.create_section(
            document_id=doc_id, heading="Section 2", body="Content 2"
        )
        assert section2.order_index == 1

        # Create third section with explicit order_index
        section3 = section_service.create_section(
            document_id=doc_id, heading="Section 3", body="Content 3", order_index=5
        )
        assert section3.order_index == 5

        # Create fourth section (should auto-increment from max)
        section4 = section_service.create_section(
            document_id=doc_id, heading="Section 4", body="Content 4"
        )
        assert section4.order_index == 6

    def test_create_nested_section(self, service):
        """Test creating a nested section."""
        section_service, doc_id = service
        # Create parent section
        parent = section_service.create_section(
            document_id=doc_id, heading="Parent", body="Parent content"
        )

        # Create child section
        child = section_service.create_section(
            document_id=doc_id,
            heading="Child",
            body="Child content",
            parent_section_id=parent.id,
        )
        assert child.parent_section_id == parent.id
        assert child.document_id == doc_id
        assert child.order_index == 0

    def test_create_section_validation_errors(self, service):
        """Test section creation validation errors."""
        section_service, doc_id = service

        # Empty heading
        with pytest.raises(ValidationError) as exc_info:
            section_service.create_section(
                document_id=doc_id, heading="", body="Content"
            )
        assert exc_info.value.field == "heading"

        # Invalid document_id
        with pytest.raises(ValidationError) as exc_info:
            section_service.create_section(
                document_id="", heading="Test", body="Content"
            )
        assert exc_info.value.field == "id"

        # Non-existent parent
        with pytest.raises(NotFoundError):
            section_service.create_section(
                document_id=doc_id,
                heading="Test",
                body="Content",
                parent_section_id="non-existent",
            )

        # Duplicate ID
        section_id = str(uuid.uuid4())
        section_service.create_section(
            document_id=doc_id,
            heading="Test",
            body="Content",
            section_id=section_id,
        )
        with pytest.raises(DuplicateError):
            section_service.create_section(
                document_id=doc_id,
                heading="Test 2",
                body="Content 2",
                section_id=section_id,
            )


class TestGetSection:
    """Tests for section retrieval."""

    def test_get_section_by_id(self, service):
        """Test getting a section by ID."""
        section_service, doc_id = service
        created = section_service.create_section(
            document_id=doc_id, heading="Test Section", body="Test content"
        )

        retrieved = section_service.get_section(created.id)
        assert retrieved.id == created.id
        assert retrieved.heading == "Test Section"

    def test_get_section_with_children(self, service):
        """Test getting a section with children."""
        section_service, doc_id = service
        parent = section_service.create_section(
            document_id=doc_id, heading="Parent", body="Parent content"
        )
        child1 = section_service.create_section(
            document_id=doc_id,
            heading="Child 1",
            body="Child 1 content",
            parent_section_id=parent.id,
        )
        child2 = section_service.create_section(
            document_id=doc_id,
            heading="Child 2",
            body="Child 2 content",
            parent_section_id=parent.id,
        )

        retrieved = section_service.get_section(parent.id, include_children=True)
        assert len(retrieved.child_sections) == 2
        assert {c.id for c in retrieved.child_sections} == {child1.id, child2.id}

    def test_get_section_not_found(self, service):
        """Test getting a non-existent section."""
        section_service, _ = service
        with pytest.raises(NotFoundError):
            section_service.get_section("non-existent-id")


class TestUpdateSection:
    """Tests for section updates."""

    def test_update_section_heading(self, service):
        """Test updating section heading."""
        section_service, doc_id = service
        section = section_service.create_section(
            document_id=doc_id, heading="Old Heading", body="Content"
        )

        updated = section_service.update_section(section.id, heading="New Heading")
        assert updated.heading == "New Heading"
        assert updated.body == "Content"  # Unchanged

    def test_update_section_body(self, service):
        """Test updating section body."""
        section_service, doc_id = service
        section = section_service.create_section(
            document_id=doc_id, heading="Heading", body="Old content"
        )

        updated = section_service.update_section(section.id, body="New content")
        assert updated.body == "New content"
        assert updated.heading == "Heading"  # Unchanged

    def test_update_section_metadata(self, service):
        """Test updating section metadata."""
        section_service, doc_id = service
        section = section_service.create_section(
            document_id=doc_id,
            heading="Heading",
            body="Content",
            metadata={"key1": "value1"},
        )

        updated = section_service.update_section(
            section.id, metadata={"key2": "value2"}
        )
        assert updated.metadata == {"key2": "value2"}

    def test_update_section_order_index(self, service):
        """Test updating section order index."""
        section_service, doc_id = service
        section = section_service.create_section(
            document_id=doc_id, heading="Heading", body="Content", order_index=0
        )

        updated = section_service.update_section(section.id, order_index=5)
        assert updated.order_index == 5


class TestDeleteSection:
    """Tests for section deletion."""

    def test_delete_section(self, service):
        """Test deleting a section."""
        section_service, doc_id = service
        section = section_service.create_section(
            document_id=doc_id, heading="Test Section", body="Content"
        )

        deleted = section_service.delete_section(section.id)
        assert deleted is True

        # Verify section is deleted
        with pytest.raises(NotFoundError):
            section_service.get_section(section.id)

    def test_delete_section_cascades_to_children(self, service):
        """Test that deleting a section cascades to children."""
        section_service, doc_id = service
        parent = section_service.create_section(
            document_id=doc_id, heading="Parent", body="Parent content"
        )
        child = section_service.create_section(
            document_id=doc_id,
            heading="Child",
            body="Child content",
            parent_section_id=parent.id,
        )

        # Delete parent
        section_service.delete_section(parent.id)

        # Verify both are deleted
        with pytest.raises(NotFoundError):
            section_service.get_section(parent.id)
        with pytest.raises(NotFoundError):
            section_service.get_section(child.id)

    def test_delete_section_not_found(self, service):
        """Test deleting a non-existent section."""
        section_service, _ = service
        deleted = section_service.delete_section("non-existent-id")
        assert deleted is False


class TestGetSectionsByDocument:
    """Tests for getting sections by document."""

    def test_get_sections_flat(self, service):
        """Test getting sections as flat list."""
        section_service, doc_id = service
        section1 = section_service.create_section(
            document_id=doc_id, heading="Section 1", body="Content 1"
        )
        section2 = section_service.create_section(
            document_id=doc_id, heading="Section 2", body="Content 2"
        )

        sections = section_service.get_sections_by_document(doc_id, flat=True)
        assert len(sections) == 2
        assert {s.id for s in sections} == {section1.id, section2.id}

    def test_get_sections_tree(self, service):
        """Test getting sections as tree structure."""
        section_service, doc_id = service
        parent = section_service.create_section(
            document_id=doc_id, heading="Parent", body="Parent content"
        )
        child = section_service.create_section(
            document_id=doc_id,
            heading="Child",
            body="Child content",
            parent_section_id=parent.id,
        )

        sections = section_service.get_sections_by_document(doc_id, flat=False)
        assert len(sections) == 1
        assert sections[0].id == parent.id
        assert len(sections[0].child_sections) == 1
        assert sections[0].child_sections[0].id == child.id

    def test_get_sections_filter_by_heading(self, service):
        """Test filtering sections by heading pattern."""
        section_service, doc_id = service
        section_service.create_section(
            document_id=doc_id, heading="Python Guide", body="Content"
        )
        section_service.create_section(
            document_id=doc_id, heading="JavaScript Guide", body="Content"
        )
        section_service.create_section(
            document_id=doc_id, heading="Python Tutorial", body="Content"
        )

        sections = section_service.get_sections_by_document(
            doc_id, flat=True, heading_pattern="Python"
        )
        assert len(sections) == 2
        assert all("Python" in s.heading for s in sections)

    def test_get_sections_filter_by_metadata(self, service):
        """Test filtering sections by metadata."""
        section_service, doc_id = service
        section_service.create_section(
            document_id=doc_id,
            heading="Section 1",
            body="Content",
            metadata={"category": "guide", "language": "python"},
        )
        section_service.create_section(
            document_id=doc_id,
            heading="Section 2",
            body="Content",
            metadata={"category": "tutorial", "language": "python"},
        )
        section_service.create_section(
            document_id=doc_id,
            heading="Section 3",
            body="Content",
            metadata={"category": "guide", "language": "javascript"},
        )

        sections = section_service.get_sections_by_document(
            doc_id, flat=True, metadata_filter={"category": "guide"}
        )
        assert len(sections) == 2
        assert all(s.metadata.get("category") == "guide" for s in sections)


class TestSearchSections:
    """Tests for full-text search."""

    def test_search_sections_by_heading(self, service):
        """Test searching sections by heading."""
        section_service, doc_id = service
        section_service.create_section(
            document_id=doc_id, heading="Python Programming", body="Content"
        )
        section_service.create_section(
            document_id=doc_id, heading="JavaScript Basics", body="Content"
        )

        results = section_service.search_sections("Python", document_id=doc_id)
        assert len(results) == 1
        assert "Python" in results[0].heading

    def test_search_sections_by_body(self, service):
        """Test searching sections by body content."""
        section_service, doc_id = service
        section_service.create_section(
            document_id=doc_id, heading="Section 1", body="Python is great"
        )
        section_service.create_section(
            document_id=doc_id, heading="Section 2", body="JavaScript is fun"
        )

        results = section_service.search_sections("Python", document_id=doc_id)
        assert len(results) == 1
        assert "Python" in results[0].body

    def test_search_sections_limit(self, service):
        """Test search result limit."""
        section_service, doc_id = service
        for i in range(10):
            section_service.create_section(
                document_id=doc_id, heading=f"Section {i}", body="Python content"
            )

        results = section_service.search_sections("Python", document_id=doc_id, limit=5)
        assert len(results) <= 5


class TestHierarchicalOperations:
    """Tests for hierarchical operations."""

    def test_update_parent_move_section(self, service):
        """Test moving a section to a different parent."""
        section_service, doc_id = service
        parent1 = section_service.create_section(
            document_id=doc_id, heading="Parent 1", body="Content"
        )
        parent2 = section_service.create_section(
            document_id=doc_id, heading="Parent 2", body="Content"
        )
        child = section_service.create_section(
            document_id=doc_id,
            heading="Child",
            body="Content",
            parent_section_id=parent1.id,
        )

        # Move child from parent1 to parent2
        updated = section_service.update_parent(child.id, parent2.id)
        assert updated.parent_section_id == parent2.id

        # Verify parent1 has no children
        parent1_retrieved = section_service.get_section(parent1.id, include_children=True)
        assert len(parent1_retrieved.child_sections) == 0

        # Verify parent2 has the child
        parent2_retrieved = section_service.get_section(parent2.id, include_children=True)
        assert len(parent2_retrieved.child_sections) == 1
        assert parent2_retrieved.child_sections[0].id == child.id

    def test_update_parent_make_top_level(self, service):
        """Test moving a section to top-level."""
        section_service, doc_id = service
        parent = section_service.create_section(
            document_id=doc_id, heading="Parent", body="Content"
        )
        child = section_service.create_section(
            document_id=doc_id,
            heading="Child",
            body="Content",
            parent_section_id=parent.id,
        )

        # Move child to top-level
        updated = section_service.update_parent(child.id, None)
        assert updated.parent_section_id is None

    def test_update_parent_prevent_cycle(self, service):
        """Test that moving a section into its own subtree is prevented."""
        section_service, doc_id = service
        parent = section_service.create_section(
            document_id=doc_id, heading="Parent", body="Content"
        )
        child = section_service.create_section(
            document_id=doc_id,
            heading="Child",
            body="Content",
            parent_section_id=parent.id,
        )
        grandchild = section_service.create_section(
            document_id=doc_id,
            heading="Grandchild",
            body="Content",
            parent_section_id=child.id,
        )

        # Try to move parent into grandchild (would create cycle)
        with pytest.raises(ValidationError) as exc_info:
            section_service.update_parent(parent.id, grandchild.id)
        assert "cycle" in str(exc_info.value).lower()

        # Try to move parent into child (would create cycle)
        with pytest.raises(ValidationError):
            section_service.update_parent(parent.id, child.id)

    def test_reorder_sections(self, service):
        """Test reordering sections within a parent."""
        section_service, doc_id = service
        parent = section_service.create_section(
            document_id=doc_id, heading="Parent", body="Content"
        )
        child1 = section_service.create_section(
            document_id=doc_id,
            heading="Child 1",
            body="Content",
            parent_section_id=parent.id,
            order_index=0,
        )
        child2 = section_service.create_section(
            document_id=doc_id,
            heading="Child 2",
            body="Content",
            parent_section_id=parent.id,
            order_index=1,
        )
        child3 = section_service.create_section(
            document_id=doc_id,
            heading="Child 3",
            body="Content",
            parent_section_id=parent.id,
            order_index=2,
        )

        # Reorder: child3, child1, child2
        updated = section_service.reorder_sections(
            parent.id, [child3.id, child1.id, child2.id]
        )
        assert len(updated) == 3
        assert updated[0].id == child3.id and updated[0].order_index == 0
        assert updated[1].id == child1.id and updated[1].order_index == 1
        assert updated[2].id == child2.id and updated[2].order_index == 2

    def test_reorder_top_level_sections(self, service):
        """Test reordering top-level sections."""
        section_service, doc_id = service
        section1 = section_service.create_section(
            document_id=doc_id, heading="Section 1", body="Content", order_index=0
        )
        section2 = section_service.create_section(
            document_id=doc_id, heading="Section 2", body="Content", order_index=1
        )
        section3 = section_service.create_section(
            document_id=doc_id, heading="Section 3", body="Content", order_index=2
        )

        # Reorder: section3, section1, section2
        updated = section_service.reorder_sections(
            None, [section3.id, section1.id, section2.id]
        )
        assert updated[0].id == section3.id and updated[0].order_index == 0
        assert updated[1].id == section1.id and updated[1].order_index == 1
        assert updated[2].id == section2.id and updated[2].order_index == 2

    def test_get_section_path(self, service):
        """Test getting path from root to section."""
        section_service, doc_id = service
        parent = section_service.create_section(
            document_id=doc_id, heading="Parent", body="Content"
        )
        child = section_service.create_section(
            document_id=doc_id,
            heading="Child",
            body="Content",
            parent_section_id=parent.id,
        )
        grandchild = section_service.create_section(
            document_id=doc_id,
            heading="Grandchild",
            body="Content",
            parent_section_id=child.id,
        )

        path = section_service.get_section_path(grandchild.id)
        assert len(path) == 3
        assert path[0].id == parent.id
        assert path[1].id == child.id
        assert path[2].id == grandchild.id

    def test_get_section_tree(self, service):
        """Test getting section with entire subtree."""
        section_service, doc_id = service
        parent = section_service.create_section(
            document_id=doc_id, heading="Parent", body="Content"
        )
        child1 = section_service.create_section(
            document_id=doc_id,
            heading="Child 1",
            body="Content",
            parent_section_id=parent.id,
        )
        child2 = section_service.create_section(
            document_id=doc_id,
            heading="Child 2",
            body="Content",
            parent_section_id=parent.id,
        )

        tree = section_service.get_section_tree(parent.id)
        assert tree.id == parent.id
        assert len(tree.child_sections) == 2
        assert {c.id for c in tree.child_sections} == {child1.id, child2.id}
