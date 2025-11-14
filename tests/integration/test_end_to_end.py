"""End-to-end integration tests for Doc-O-Matic workflows."""

import uuid

import pytest

pytestmark = pytest.mark.integration

from docomatic.services.document_service import DocumentService
from docomatic.services.link_service import LinkService
from docomatic.services.section_service import SectionService


class TestDocumentWorkflow:
    """Test complete document creation and management workflows."""

    def test_create_document_with_sections_and_links(self, temp_db):
        """Test creating a document with sections and links in one workflow."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            link_service = LinkService(session)
            
            # Create document
            doc = doc_service.create_document(
                title="API Documentation",
                metadata={"version": "1.0", "author": "test"}
            )
            
            # Create sections
            intro = section_service.create_section(
                document_id=doc.id,
                heading="Introduction",
                body="This is the introduction."
            )
            main = section_service.create_section(
                document_id=doc.id,
                heading="Main Content",
                body="This is the main content."
            )
            nested = section_service.create_section(
                document_id=doc.id,
                heading="Details",
                body="Detailed information.",
                parent_section_id=main.id
            )
            
            # Create links
            link1 = link_service.link_section(
                section_id=intro.id,
                link_type="todo-rama",
                link_target="todo-rama://task/123"
            )
            link2 = link_service.link_section(
                section_id=main.id,
                link_type="github",
                link_target="github://repo/api.py"
            )
            
            # Verify everything is connected
            retrieved_doc = doc_service.get_document(doc.id, include_sections=True, include_links=True)
            assert retrieved_doc.title == "API Documentation"
            assert len(retrieved_doc.sections) == 2  # Top-level sections
            assert len(retrieved_doc.links) == 2
            
            # Verify hierarchy
            main_section = next(s for s in retrieved_doc.sections if s.id == main.id)
            assert len(main_section.child_sections) == 1
            assert main_section.child_sections[0].id == nested.id

    def test_update_document_structure(self, temp_db):
        """Test updating document structure (sections, links)."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            link_service = LinkService(session)
            
            # Create initial document
            doc = doc_service.create_document(title="Initial Document")
            section = section_service.create_section(
                document_id=doc.id,
                heading="Initial Section",
                body="Initial content"
            )
            
            # Update document
            doc_service.update_document(doc.id, title="Updated Document")
            
            # Update section
            section_service.update_section(section.id, heading="Updated Section", body="Updated content")
            
            # Add link
            link_service.link_section(
                section_id=section.id,
                link_type="todo-rama",
                link_target="todo-rama://task/456"
            )
            
            # Verify updates
            retrieved = doc_service.get_document(doc.id, include_sections=True, include_links=True)
            assert retrieved.title == "Updated Document"
            assert retrieved.sections[0].heading == "Updated Section"
            assert len(retrieved.sections[0].links) == 1

    def test_delete_document_cascades(self, temp_db):
        """Test that deleting a document cascades to sections and links."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            link_service = LinkService(session)
            
            # Create document with sections and links
            doc = doc_service.create_document(title="Document to Delete")
            section1 = section_service.create_section(
                document_id=doc.id,
                heading="Section 1",
                body="Content 1"
            )
            section2 = section_service.create_section(
                document_id=doc.id,
                heading="Section 2",
                body="Content 2",
                parent_section_id=section1.id
            )
            link = link_service.link_section(
                section_id=section1.id,
                link_type="todo-rama",
                link_target="todo-rama://task/789"
            )
            
            # Delete document
            doc_service.delete_document(doc.id)
            
            # Verify everything is deleted
            with pytest.raises(Exception):  # NotFoundError
                doc_service.get_document(doc.id)
            
            with pytest.raises(Exception):  # NotFoundError
                section_service.get_section(section1.id)
            
            with pytest.raises(Exception):  # NotFoundError
                section_service.get_section(section2.id)
            
            # Links should also be deleted (cascade)
            links = link_service.get_section_links(section1.id)
            assert len(links) == 0


class TestHierarchicalWorkflow:
    """Test hierarchical section management workflows."""

    def test_create_deep_hierarchy(self, temp_db):
        """Test creating a deep section hierarchy."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            doc = doc_service.create_document(title="Deep Hierarchy Document")
            
            # Create 4-level hierarchy
            level1 = section_service.create_section(
                document_id=doc.id,
                heading="Level 1",
                body="Level 1 content"
            )
            level2 = section_service.create_section(
                document_id=doc.id,
                heading="Level 2",
                body="Level 2 content",
                parent_section_id=level1.id
            )
            level3 = section_service.create_section(
                document_id=doc.id,
                heading="Level 3",
                body="Level 3 content",
                parent_section_id=level2.id
            )
            level4 = section_service.create_section(
                document_id=doc.id,
                heading="Level 4",
                body="Level 4 content",
                parent_section_id=level3.id
            )
            
            # Verify hierarchy
            tree = section_service.get_sections_by_document(doc.id, flat=False)
            assert len(tree) == 1
            assert tree[0].id == level1.id
            
            # Navigate down the tree
            l1 = tree[0]
            assert len(l1.child_sections) == 1
            l2 = l1.child_sections[0]
            assert l2.id == level2.id
            assert len(l2.child_sections) == 1
            l3 = l2.child_sections[0]
            assert l3.id == level3.id
            assert len(l3.child_sections) == 1
            l4 = l3.child_sections[0]
            assert l4.id == level4.id

    def test_move_section_in_hierarchy(self, temp_db):
        """Test moving sections within hierarchy."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            doc = doc_service.create_document(title="Move Test Document")
            
            parent1 = section_service.create_section(
                document_id=doc.id,
                heading="Parent 1",
                body="Parent 1 content"
            )
            parent2 = section_service.create_section(
                document_id=doc.id,
                heading="Parent 2",
                body="Parent 2 content"
            )
            child = section_service.create_section(
                document_id=doc.id,
                heading="Child",
                body="Child content",
                parent_section_id=parent1.id
            )
            
            # Move child from parent1 to parent2
            section_service.update_parent(child.id, parent2.id)
            
            # Verify move
            tree = section_service.get_sections_by_document(doc.id, flat=False)
            p1 = next(s for s in tree if s.id == parent1.id)
            p2 = next(s for s in tree if s.id == parent2.id)
            
            assert len(p1.child_sections) == 0
            assert len(p2.child_sections) == 1
            assert p2.child_sections[0].id == child.id

    def test_reorder_sections(self, temp_db):
        """Test reordering sections."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            doc = doc_service.create_document(title="Reorder Test Document")
            
            parent = section_service.create_section(
                document_id=doc.id,
                heading="Parent",
                body="Parent content"
            )
            
            child1 = section_service.create_section(
                document_id=doc.id,
                heading="Child 1",
                body="Content 1",
                parent_section_id=parent.id,
                order_index=0
            )
            child2 = section_service.create_section(
                document_id=doc.id,
                heading="Child 2",
                body="Content 2",
                parent_section_id=parent.id,
                order_index=1
            )
            child3 = section_service.create_section(
                document_id=doc.id,
                heading="Child 3",
                body="Content 3",
                parent_section_id=parent.id,
                order_index=2
            )
            
            # Reorder: child3, child1, child2
            section_service.reorder_sections(parent.id, [child3.id, child1.id, child2.id])
            
            # Verify order
            tree = section_service.get_sections_by_document(doc.id, flat=False)
            parent_retrieved = tree[0]
            children = parent_retrieved.child_sections
            
            assert children[0].id == child3.id and children[0].order_index == 0
            assert children[1].id == child1.id and children[1].order_index == 1
            assert children[2].id == child2.id and children[2].order_index == 2


class TestLinkWorkflow:
    """Test link management workflows."""

    def test_link_multiple_sections_to_same_task(self, temp_db):
        """Test linking multiple sections to the same task."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            link_service = LinkService(session)
            
            doc = doc_service.create_document(title="Multi-Link Document")
            
            section1 = section_service.create_section(
                document_id=doc.id,
                heading="Section 1",
                body="Content 1"
            )
            section2 = section_service.create_section(
                document_id=doc.id,
                heading="Section 2",
                body="Content 2"
            )
            section3 = section_service.create_section(
                document_id=doc.id,
                heading="Section 3",
                body="Content 3"
            )
            
            # Link all to same task
            task_target = "todo-rama://task/123"
            link1 = link_service.link_section(section1.id, "todo-rama", task_target)
            link2 = link_service.link_section(section2.id, "todo-rama", task_target)
            link3 = link_service.link_section(section3.id, "todo-rama", task_target)
            
            # Find all sections linked to this task
            results = link_service.get_sections_by_link("todo-rama", task_target)
            assert len(results) == 3
            section_ids = {r["section_id"] for r in results}
            assert {section1.id, section2.id, section3.id} == section_ids

    def test_link_workflow_with_metadata(self, temp_db):
        """Test link workflow with metadata updates."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            link_service = LinkService(session)
            
            doc = doc_service.create_document(title="Link Metadata Document")
            section = section_service.create_section(
                document_id=doc.id,
                heading="Section",
                body="Content"
            )
            
            # Create link with metadata
            link = link_service.link_section(
                section_id=section.id,
                link_type="todo-rama",
                link_target="todo-rama://task/123",
                link_metadata={"title": "Task", "status": "open"}
            )
            
            # Retrieve and verify
            links = link_service.get_section_links(section.id)
            assert len(links) == 1
            assert links[0].link_metadata["title"] == "Task"
            assert links[0].link_metadata["status"] == "open"
            
            # Unlink
            result = link_service.unlink_section(link.id)
            assert result is True
            
            # Verify unlinked
            links = link_service.get_section_links(section.id)
            assert len(links) == 0


class TestSearchWorkflow:
    """Test search and retrieval workflows."""

    def test_search_across_multiple_documents(self, temp_db):
        """Test searching sections across multiple documents."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            # Create multiple documents
            doc1 = doc_service.create_document(title="Python Guide")
            doc2 = doc_service.create_document(title="JavaScript Guide")
            
            # Create sections with searchable content
            section_service.create_section(
                document_id=doc1.id,
                heading="Python Basics",
                body="Python is a programming language"
            )
            section_service.create_section(
                document_id=doc1.id,
                heading="Python Advanced",
                body="Advanced Python programming techniques"
            )
            section_service.create_section(
                document_id=doc2.id,
                heading="JavaScript Basics",
                body="JavaScript is a programming language"
            )
            
            # Search for "Python" across all documents
            results = section_service.search_sections("Python")
            assert len(results) >= 2
            assert all("Python" in r.heading or "Python" in r.body for r in results)
            
            # Search within specific document
            results = section_service.search_sections("Python", document_id=doc1.id)
            assert len(results) == 2

    def test_filter_and_search_combination(self, temp_db):
        """Test combining filters with search."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            doc = doc_service.create_document(title="Filter Test Document")
            
            # Create sections with metadata
            section_service.create_section(
                document_id=doc.id,
                heading="Python Guide",
                body="Python programming guide",
                metadata={"category": "guide", "language": "python"}
            )
            section_service.create_section(
                document_id=doc.id,
                heading="Python Tutorial",
                body="Python tutorial content",
                metadata={"category": "tutorial", "language": "python"}
            )
            section_service.create_section(
                document_id=doc.id,
                heading="JavaScript Guide",
                body="JavaScript programming guide",
                metadata={"category": "guide", "language": "javascript"}
            )
            
            # Filter by metadata and search
            sections = section_service.get_sections_by_document(
                doc.id,
                flat=True,
                metadata_filter={"category": "guide"}
            )
            assert len(sections) == 2
            
            # Search within filtered results
            python_sections = [s for s in sections if "Python" in s.heading]
            assert len(python_sections) == 1
