"""Comprehensive tests for link service CRUD operations."""

import uuid

import pytest

pytestmark = pytest.mark.unit

from docomatic.exceptions import (
    DatabaseError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from docomatic.models.link import Link
from docomatic.services.document_service import DocumentService
from docomatic.services.link_service import LinkService
from docomatic.services.section_service import SectionService


class TestLinkSection:
    """Tests for linking sections to external resources."""

    def test_link_section_basic(self, link_service, sample_document_with_sections):
        """Test creating a basic link."""
        doc, sections = sample_document_with_sections
        link = link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target="todo-rama://task/123"
        )
        assert link.id is not None
        assert link.section_id == sections[0].id
        assert link.document_id == doc.id
        assert link.link_type == "todo-rama"
        assert link.link_target == "todo-rama://task/123"

    def test_link_section_with_metadata(self, link_service, sample_document_with_sections):
        """Test creating a link with metadata."""
        doc, sections = sample_document_with_sections
        metadata = {"title": "Test Task", "status": "in_progress"}
        link = link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target="todo-rama://task/123",
            link_metadata=metadata
        )
        assert link.link_metadata == metadata

    def test_link_section_bucket_o_facts(self, link_service, sample_document_with_sections):
        """Test linking to Bucket-O-Facts."""
        doc, sections = sample_document_with_sections
        link = link_service.link_section(
            section_id=sections[0].id,
            link_type="bucket-o-facts",
            link_target="bucket-o-facts://fact/456"
        )
        assert link.link_type == "bucket-o-facts"
        assert link.link_target == "bucket-o-facts://fact/456"

    def test_link_section_github(self, link_service, sample_document_with_sections):
        """Test linking to GitHub."""
        doc, sections = sample_document_with_sections
        link = link_service.link_section(
            section_id=sections[0].id,
            link_type="github",
            link_target="github://repo/file.py#L123"
        )
        assert link.link_type == "github"
        assert link.link_target == "github://repo/file.py#L123"

    def test_link_section_with_custom_id(self, link_service, sample_document_with_sections):
        """Test creating a link with custom ID."""
        doc, sections = sample_document_with_sections
        custom_id = str(uuid.uuid4())
        link = link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target="todo-rama://task/123",
            link_id=custom_id
        )
        assert link.id == custom_id

    def test_link_section_duplicate_id(self, link_service, sample_document_with_sections):
        """Test that duplicate link ID raises error."""
        doc, sections = sample_document_with_sections
        link_id = str(uuid.uuid4())
        link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target="todo-rama://task/123",
            link_id=link_id
        )
        
        with pytest.raises(DuplicateError) as exc_info:
            link_service.link_section(
                section_id=sections[1].id,
                link_type="todo-rama",
                link_target="todo-rama://task/456",
                link_id=link_id
            )
        assert "already exists" in str(exc_info.value)

    def test_link_section_invalid_section_id(self, link_service):
        """Test linking with invalid section ID raises error."""
        with pytest.raises(ValidationError) as exc_info:
            link_service.link_section(
                section_id="",
                link_type="todo-rama",
                link_target="todo-rama://task/123"
            )
        assert exc_info.value.field == "id"

    def test_link_section_nonexistent_section(self, link_service):
        """Test linking to non-existent section raises error."""
        with pytest.raises(NotFoundError) as exc_info:
            link_service.link_section(
                section_id=str(uuid.uuid4()),
                link_type="todo-rama",
                link_target="todo-rama://task/123"
            )
        assert "Section" in str(exc_info.value)

    def test_link_section_invalid_link_type(self, link_service, sample_document_with_sections):
        """Test linking with invalid link type raises error."""
        doc, sections = sample_document_with_sections
        with pytest.raises(ValidationError) as exc_info:
            link_service.link_section(
                section_id=sections[0].id,
                link_type="invalid-type",
                link_target="target"
            )
        assert exc_info.value.field == "link_type"

    def test_link_section_empty_link_type(self, link_service, sample_document_with_sections):
        """Test linking with empty link type raises error."""
        doc, sections = sample_document_with_sections
        with pytest.raises(ValidationError) as exc_info:
            link_service.link_section(
                section_id=sections[0].id,
                link_type="",
                link_target="target"
            )
        assert exc_info.value.field == "link_type"

    def test_link_section_empty_link_target(self, link_service, sample_document_with_sections):
        """Test linking with empty link target raises error."""
        doc, sections = sample_document_with_sections
        with pytest.raises(ValidationError) as exc_info:
            link_service.link_section(
                section_id=sections[0].id,
                link_type="todo-rama",
                link_target=""
            )
        assert exc_info.value.field == "link_target"

    def test_link_section_link_target_too_long(self, link_service, sample_document_with_sections):
        """Test linking with link target exceeding max length raises error."""
        doc, sections = sample_document_with_sections
        long_target = "a" * 501
        with pytest.raises(ValidationError) as exc_info:
            link_service.link_section(
                section_id=sections[0].id,
                link_type="todo-rama",
                link_target=long_target
            )
        assert "at most 500 characters" in str(exc_info.value)

    def test_link_section_invalid_metadata(self, link_service, sample_document_with_sections):
        """Test linking with invalid metadata raises error."""
        doc, sections = sample_document_with_sections
        with pytest.raises(ValidationError) as exc_info:
            link_service.link_section(
                section_id=sections[0].id,
                link_type="todo-rama",
                link_target="target",
                link_metadata="not a dict"  # type: ignore
            )
        assert exc_info.value.field == "metadata"


class TestUnlinkSection:
    """Tests for unlinking sections."""

    def test_unlink_section(self, link_service, sample_link):
        """Test unlinking a section."""
        result = link_service.unlink_section(sample_link.id)
        assert result is True

    def test_unlink_section_not_found(self, link_service):
        """Test unlinking non-existent link returns False."""
        result = link_service.unlink_section(str(uuid.uuid4()))
        assert result is False

    def test_unlink_section_invalid_id(self, link_service):
        """Test unlinking with invalid ID raises error."""
        with pytest.raises(ValidationError):
            link_service.unlink_section("")


class TestGetSectionLinks:
    """Tests for retrieving section links."""

    def test_get_section_links_single(self, link_service, sample_document_with_sections):
        """Test getting links for a section with one link."""
        doc, sections = sample_document_with_sections
        link = link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target="todo-rama://task/123"
        )
        
        links = link_service.get_section_links(sections[0].id)
        assert len(links) == 1
        assert links[0].id == link.id

    def test_get_section_links_multiple(self, link_service, sample_document_with_sections):
        """Test getting links for a section with multiple links."""
        doc, sections = sample_document_with_sections
        link1 = link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target="todo-rama://task/123"
        )
        link2 = link_service.link_section(
            section_id=sections[0].id,
            link_type="bucket-o-facts",
            link_target="bucket-o-facts://fact/456"
        )
        link3 = link_service.link_section(
            section_id=sections[0].id,
            link_type="github",
            link_target="github://repo/file.py"
        )
        
        links = link_service.get_section_links(sections[0].id)
        assert len(links) == 3
        link_ids = {l.id for l in links}
        assert {link1.id, link2.id, link3.id} == link_ids

    def test_get_section_links_empty(self, link_service, sample_document_with_sections):
        """Test getting links for a section with no links."""
        doc, sections = sample_document_with_sections
        links = link_service.get_section_links(sections[0].id)
        assert links == []

    def test_get_section_links_invalid_id(self, link_service):
        """Test getting links with invalid section ID raises error."""
        with pytest.raises(ValidationError):
            link_service.get_section_links("")


class TestGetSectionsByLink:
    """Tests for finding sections by link."""

    def test_get_sections_by_link_single(self, link_service, sample_document_with_sections):
        """Test finding sections linked to a specific target."""
        doc, sections = sample_document_with_sections
        link_target = "todo-rama://task/123"
        link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target=link_target
        )
        
        results = link_service.get_sections_by_link("todo-rama", link_target)
        assert len(results) == 1
        assert results[0]["section_id"] == sections[0].id
        assert results[0]["link_target"] == link_target

    def test_get_sections_by_link_multiple(self, link_service, temp_db):
        """Test finding multiple sections linked to the same target."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            link_service = LinkService(session)
            
            # Create multiple documents and sections
            doc1 = doc_service.create_document(title="Doc 1")
            doc2 = doc_service.create_document(title="Doc 2")
            
            section1 = section_service.create_section(
                document_id=doc1.id,
                heading="Section 1",
                body="Content 1"
            )
            section2 = section_service.create_section(
                document_id=doc2.id,
                heading="Section 2",
                body="Content 2"
            )
            
            # Link both to same target
            link_target = "todo-rama://task/123"
            link_service.link_section(
                section_id=section1.id,
                link_type="todo-rama",
                link_target=link_target
            )
            link_service.link_section(
                section_id=section2.id,
                link_type="todo-rama",
                link_target=link_target
            )
            
            results = link_service.get_sections_by_link("todo-rama", link_target)
            assert len(results) == 2
            section_ids = {r["section_id"] for r in results}
            assert {section1.id, section2.id} == section_ids

    def test_get_sections_by_link_not_found(self, link_service):
        """Test finding sections by non-existent link returns empty list."""
        results = link_service.get_sections_by_link(
            "todo-rama",
            "todo-rama://task/nonexistent"
        )
        assert results == []

    def test_get_sections_by_link_invalid_type(self, link_service):
        """Test finding sections with invalid link type raises error."""
        with pytest.raises(ValidationError):
            link_service.get_sections_by_link("invalid-type", "target")

    def test_get_sections_by_link_invalid_target(self, link_service):
        """Test finding sections with invalid target raises error."""
        with pytest.raises(ValidationError):
            link_service.get_sections_by_link("todo-rama", "")

    def test_get_sections_by_link_different_types(self, link_service, sample_document_with_sections):
        """Test that different link types are handled separately."""
        doc, sections = sample_document_with_sections
        target = "resource-123"
        
        link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target=target
        )
        link_service.link_section(
            section_id=sections[1].id,
            link_type="bucket-o-facts",
            link_target=target
        )
        
        todo_results = link_service.get_sections_by_link("todo-rama", target)
        bucket_results = link_service.get_sections_by_link("bucket-o-facts", target)
        
        assert len(todo_results) == 1
        assert len(bucket_results) == 1
        assert todo_results[0]["section_id"] == sections[0].id
        assert bucket_results[0]["section_id"] == sections[1].id


class TestLinkValidation:
    """Tests for link validation logic."""

    def test_link_type_validation_all_types(self, link_service, sample_document_with_sections):
        """Test that all valid link types are accepted."""
        doc, sections = sample_document_with_sections
        valid_types = ["todo-rama", "bucket-o-facts", "github"]
        
        for link_type in valid_types:
            link = link_service.link_section(
                section_id=sections[0].id,
                link_type=link_type,
                link_target=f"{link_type}://target/123"
            )
            assert link.link_type == link_type

    def test_link_metadata_structure(self, link_service, sample_document_with_sections):
        """Test that link metadata can contain nested structures."""
        doc, sections = sample_document_with_sections
        complex_metadata = {
            "title": "Task",
            "status": "in_progress",
            "assignee": {"name": "John", "email": "john@example.com"},
            "tags": ["urgent", "backend"]
        }
        
        link = link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target="todo-rama://task/123",
            link_metadata=complex_metadata
        )
        assert link.link_metadata == complex_metadata


class TestLinkDocument:
    """Tests for linking documents to external resources."""

    def test_link_document_basic(self, link_service, sample_document):
        """Test creating a basic document link."""
        link = link_service.link_document(
            document_id=sample_document.id,
            link_type="todo-rama",
            link_target="todo-rama://task/123"
        )
        assert link.id is not None
        assert link.document_id == sample_document.id
        assert link.section_id is None
        assert link.link_type == "todo-rama"
        assert link.link_target == "todo-rama://task/123"

    def test_link_document_with_metadata(self, link_service, sample_document):
        """Test creating a document link with metadata."""
        metadata = {"title": "Test Task", "status": "in_progress"}
        link = link_service.link_document(
            document_id=sample_document.id,
            link_type="todo-rama",
            link_target="todo-rama://task/123",
            link_metadata=metadata
        )
        assert link.link_metadata == metadata

    def test_link_document_duplicate_prevention(self, link_service, sample_document):
        """Test that duplicate document links are prevented."""
        link_service.link_document(
            document_id=sample_document.id,
            link_type="todo-rama",
            link_target="todo-rama://task/123"
        )
        
        with pytest.raises(DuplicateError):
            link_service.link_document(
                document_id=sample_document.id,
                link_type="todo-rama",
                link_target="todo-rama://task/123"
            )

    def test_link_document_invalid_document_id(self, link_service):
        """Test linking with invalid document ID raises error."""
        with pytest.raises(ValidationError) as exc_info:
            link_service.link_document(
                document_id="",
                link_type="todo-rama",
                link_target="todo-rama://task/123"
            )
        assert exc_info.value.field == "id"

    def test_link_document_nonexistent_document(self, link_service):
        """Test linking to non-existent document raises error."""
        with pytest.raises(NotFoundError) as exc_info:
            link_service.link_document(
                document_id=str(uuid.uuid4()),
                link_type="todo-rama",
                link_target="todo-rama://task/123"
            )
        assert "Document" in str(exc_info.value)


class TestUnlinkDocument:
    """Tests for unlinking documents."""

    def test_unlink_document(self, link_service, sample_document):
        """Test unlinking a document."""
        link = link_service.link_document(
            document_id=sample_document.id,
            link_type="todo-rama",
            link_target="todo-rama://task/123"
        )
        result = link_service.unlink_document(link.id)
        assert result is True

    def test_unlink_document_not_found(self, link_service):
        """Test unlinking non-existent link returns False."""
        result = link_service.unlink_document(str(uuid.uuid4()))
        assert result is False


class TestGetDocumentLinks:
    """Tests for retrieving document links."""

    def test_get_document_links_single(self, link_service, sample_document):
        """Test getting links for a document with one link."""
        link = link_service.link_document(
            document_id=sample_document.id,
            link_type="todo-rama",
            link_target="todo-rama://task/123"
        )
        
        links = link_service.get_document_links(sample_document.id)
        assert len(links) == 1
        assert links[0].id == link.id

    def test_get_document_links_multiple(self, link_service, sample_document):
        """Test getting links for a document with multiple links."""
        link1 = link_service.link_document(
            document_id=sample_document.id,
            link_type="todo-rama",
            link_target="todo-rama://task/123"
        )
        link2 = link_service.link_document(
            document_id=sample_document.id,
            link_type="bucket-o-facts",
            link_target="bucket-o-facts://fact/456"
        )
        link3 = link_service.link_document(
            document_id=sample_document.id,
            link_type="github",
            link_target="github://owner/repo/commit/abc123"
        )
        
        links = link_service.get_document_links(sample_document.id)
        assert len(links) == 3
        link_ids = {l.id for l in links}
        assert {link1.id, link2.id, link3.id} == link_ids


class TestGetDocumentsByLink:
    """Tests for finding documents by link."""

    def test_get_documents_by_link_single(self, link_service, temp_db):
        """Test finding documents linked to a specific target."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            link_service = LinkService(session)
            
            doc = doc_service.create_document(title="Doc 1")
            link_target = "todo-rama://task/123"
            link_service.link_document(
                document_id=doc.id,
                link_type="todo-rama",
                link_target=link_target
            )
            
            results = link_service.get_documents_by_link("todo-rama", link_target)
            assert len(results) == 1
            assert results[0]["document_id"] == doc.id
            assert results[0]["title"] == "Doc 1"


class TestGetLinksByType:
    """Tests for getting links by type."""

    def test_get_links_by_type(self, link_service, temp_db):
        """Test getting links filtered by type."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            link_service = LinkService(session)
            
            doc = doc_service.create_document(title="Doc 1")
            section = section_service.create_section(
                document_id=doc.id,
                heading="Section 1",
                body="Content"
            )
            
            # Create links of different types
            link_service.link_section(
                section_id=section.id,
                link_type="todo-rama",
                link_target="todo-rama://task/123"
            )
            link_service.link_section(
                section_id=section.id,
                link_type="bucket-o-facts",
                link_target="bucket-o-facts://fact/456"
            )
            link_service.link_section(
                section_id=section.id,
                link_type="github",
                link_target="github://owner/repo/commit/abc123"
            )
            
            # Get only todo-rama links
            todo_links = link_service.get_links_by_type("todo-rama")
            assert len(todo_links) == 1
            assert todo_links[0].link_type == "todo-rama"


class TestUpdateLinkMetadata:
    """Tests for updating link metadata."""

    def test_update_link_metadata(self, link_service, sample_link):
        """Test updating link metadata."""
        new_metadata = {"title": "Updated Task", "status": "completed"}
        updated_link = link_service.update_link_metadata(
            link_id=sample_link.id,
            link_metadata=new_metadata
        )
        assert updated_link.link_metadata == new_metadata

    def test_update_link_metadata_not_found(self, link_service):
        """Test updating metadata for non-existent link raises error."""
        with pytest.raises(NotFoundError):
            link_service.update_link_metadata(
                link_id=str(uuid.uuid4()),
                link_metadata={"title": "Test"}
            )


class TestLinkFormatValidation:
    """Tests for link URL format validation."""

    def test_todo_rama_format_valid(self, link_service, sample_document_with_sections):
        """Test valid Todo-Rama link formats."""
        doc, sections = sample_document_with_sections
        valid_formats = [
            "todo-rama://task/123",
            "todo-rama://project/task/456",
        ]
        
        for link_target in valid_formats:
            link = link_service.link_section(
                section_id=sections[0].id,
                link_type="todo-rama",
                link_target=link_target
            )
            assert link.link_target == link_target

    def test_todo_rama_format_invalid(self, link_service, sample_document_with_sections):
        """Test invalid Todo-Rama link formats."""
        doc, sections = sample_document_with_sections
        invalid_formats = [
            "todo-rama://invalid",
            "todo-rama://task/",
            "http://todo-rama/task/123",
        ]
        
        for link_target in invalid_formats:
            with pytest.raises(ValidationError) as exc_info:
                link_service.link_section(
                    section_id=sections[0].id,
                    link_type="todo-rama",
                    link_target=link_target
                )
            assert exc_info.value.field == "link_target"

    def test_bucket_o_facts_format_valid(self, link_service, sample_document_with_sections):
        """Test valid Bucket-O-Facts link formats."""
        doc, sections = sample_document_with_sections
        link = link_service.link_section(
            section_id=sections[0].id,
            link_type="bucket-o-facts",
            link_target="bucket-o-facts://fact/456"
        )
        assert link.link_target == "bucket-o-facts://fact/456"

    def test_bucket_o_facts_format_invalid(self, link_service, sample_document_with_sections):
        """Test invalid Bucket-O-Facts link formats."""
        doc, sections = sample_document_with_sections
        invalid_formats = [
            "bucket-o-facts://invalid",
            "bucket-o-facts://fact/",
        ]
        
        for link_target in invalid_formats:
            with pytest.raises(ValidationError) as exc_info:
                link_service.link_section(
                    section_id=sections[0].id,
                    link_type="bucket-o-facts",
                    link_target=link_target
                )
            assert exc_info.value.field == "link_target"

    def test_github_format_valid(self, link_service, sample_document_with_sections):
        """Test valid GitHub link formats."""
        doc, sections = sample_document_with_sections
        valid_formats = [
            "github://owner/repo/commit/abc123def456",
            "github://owner/repo/pull/123",
            "github://owner/repo/issues/456",
            "github://owner/repo/blob/path/to/file.py",
        ]
        
        for link_target in valid_formats:
            link = link_service.link_section(
                section_id=sections[0].id,
                link_type="github",
                link_target=link_target
            )
            assert link.link_target == link_target

    def test_github_format_invalid(self, link_service, sample_document_with_sections):
        """Test invalid GitHub link formats."""
        doc, sections = sample_document_with_sections
        invalid_formats = [
            "github://invalid",
            "github://owner/repo",
            "http://github.com/owner/repo",
        ]
        
        for link_target in invalid_formats:
            with pytest.raises(ValidationError) as exc_info:
                link_service.link_section(
                    section_id=sections[0].id,
                    link_type="github",
                    link_target=link_target
                )
            assert exc_info.value.field == "link_target"


class TestDuplicateLinkPrevention:
    """Tests for duplicate link prevention."""

    def test_duplicate_section_link_prevention(self, link_service, sample_document_with_sections):
        """Test that duplicate section links are prevented."""
        doc, sections = sample_document_with_sections
        link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target="todo-rama://task/123"
        )
        
        with pytest.raises(DuplicateError):
            link_service.link_section(
                section_id=sections[0].id,
                link_type="todo-rama",
                link_target="todo-rama://task/123"
            )

    def test_different_sections_same_link_allowed(self, link_service, sample_document_with_sections):
        """Test that same link can be used for different sections."""
        doc, sections = sample_document_with_sections
        link1 = link_service.link_section(
            section_id=sections[0].id,
            link_type="todo-rama",
            link_target="todo-rama://task/123"
        )
        link2 = link_service.link_section(
            section_id=sections[1].id,
            link_type="todo-rama",
            link_target="todo-rama://task/123"
        )
        assert link1.id != link2.id


class TestGenerateLinkReport:
    """Tests for link report generation."""

    def test_generate_link_report_all(self, link_service, temp_db):
        """Test generating a link report for all links."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            link_service = LinkService(session)
            
            doc = doc_service.create_document(title="Doc 1")
            section = section_service.create_section(
                document_id=doc.id,
                heading="Section 1",
                body="Content"
            )
            
            # Create various links
            link_service.link_section(
                section_id=section.id,
                link_type="todo-rama",
                link_target="todo-rama://task/123"
            )
            link_service.link_section(
                section_id=section.id,
                link_type="bucket-o-facts",
                link_target="bucket-o-facts://fact/456"
            )
            link_service.link_document(
                document_id=doc.id,
                link_type="github",
                link_target="github://owner/repo/commit/abc123"
            )
            
            report = link_service.generate_link_report()
            assert report["total_links"] == 3
            assert report["by_type"]["todo-rama"] == 1
            assert report["by_type"]["bucket-o-facts"] == 1
            assert report["by_type"]["github"] == 1
            assert report["section_links"] == 2
            assert report["document_links"] == 1

    def test_generate_link_report_by_document(self, link_service, temp_db):
        """Test generating a link report filtered by document."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            link_service = LinkService(session)
            
            doc1 = doc_service.create_document(title="Doc 1")
            doc2 = doc_service.create_document(title="Doc 2")
            section1 = section_service.create_section(
                document_id=doc1.id,
                heading="Section 1",
                body="Content"
            )
            
            link_service.link_section(
                section_id=section1.id,
                link_type="todo-rama",
                link_target="todo-rama://task/123"
            )
            link_service.link_document(
                document_id=doc2.id,
                link_type="todo-rama",
                link_target="todo-rama://task/456"
            )
            
            report = link_service.generate_link_report(document_id=doc1.id)
            assert report["total_links"] == 1

    def test_generate_link_report_by_type(self, link_service, temp_db):
        """Test generating a link report filtered by type."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            link_service = LinkService(session)
            
            doc = doc_service.create_document(title="Doc 1")
            section = section_service.create_section(
                document_id=doc.id,
                heading="Section 1",
                body="Content"
            )
            
            link_service.link_section(
                section_id=section.id,
                link_type="todo-rama",
                link_target="todo-rama://task/123"
            )
            link_service.link_section(
                section_id=section.id,
                link_type="bucket-o-facts",
                link_target="bucket-o-facts://fact/456"
            )
            
            report = link_service.generate_link_report(link_type="todo-rama")
            assert report["total_links"] == 1
            assert "todo-rama" in report["by_type"]
            assert report["by_type"]["todo-rama"] == 1
