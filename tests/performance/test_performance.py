"""Performance tests for Doc-O-Matic."""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

pytestmark = [pytest.mark.performance, pytest.mark.slow]

from docomatic.services.document_service import DocumentService
from docomatic.services.section_service import SectionService
from docomatic.services.link_service import LinkService
from tests.conftest import TestDataGenerator


class TestLargeDocumentHandling:
    """Test performance with large documents."""

    def test_create_document_with_many_sections(self, temp_db):
        """Test creating a document with many sections."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            # Create document
            doc = doc_service.create_document(title="Large Document")
            
            # Create 100 sections
            start_time = time.time()
            for i in range(100):
                section_service.create_section(
                    document_id=doc.id,
                    heading=f"Section {i}",
                    body=f"Content for section {i}",
                    order_index=i
                )
            elapsed = time.time() - start_time
            
            # Should complete in reasonable time (< 5 seconds)
            assert elapsed < 5.0, f"Creating 100 sections took {elapsed:.2f}s"
            
            # Verify all sections exist
            sections = section_service.get_sections_by_document(doc.id, flat=True)
            assert len(sections) == 100

    def test_retrieve_document_with_many_sections(self, temp_db):
        """Test retrieving a document with many sections."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            # Create document with 50 sections
            doc = doc_service.create_document(title="Document with Many Sections")
            for i in range(50):
                section_service.create_section(
                    document_id=doc.id,
                    heading=f"Section {i}",
                    body=f"Content {i}",
                    order_index=i
                )
            
            # Measure retrieval time
            start_time = time.time()
            retrieved = doc_service.get_document(doc.id, include_sections=True)
            elapsed = time.time() - start_time
            
            # Should be fast (< 1 second)
            assert elapsed < 1.0, f"Retrieving document with 50 sections took {elapsed:.2f}s"
            assert len(retrieved.sections) == 50

    def test_search_large_document(self, temp_db):
        """Test searching within a large document."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            # Create document with 200 sections
            doc = doc_service.create_document(title="Searchable Document")
            for i in range(200):
                content = f"Python programming" if i % 10 == 0 else f"Content {i}"
                section_service.create_section(
                    document_id=doc.id,
                    heading=f"Section {i}",
                    body=content,
                    order_index=i
                )
            
            # Search for "Python"
            start_time = time.time()
            results = section_service.search_sections("Python", document_id=doc.id)
            elapsed = time.time() - start_time
            
            # Should be fast (< 2 seconds)
            assert elapsed < 2.0, f"Searching 200 sections took {elapsed:.2f}s"
            assert len(results) == 20  # Every 10th section


class TestDeepHierarchyPerformance:
    """Test performance with deep section hierarchies."""

    def test_create_deep_hierarchy(self, temp_db):
        """Test creating a very deep section hierarchy."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            doc = doc_service.create_document(title="Deep Hierarchy Document")
            
            # Create 10-level deep hierarchy
            start_time = time.time()
            parent_id = None
            for level in range(10):
                section = section_service.create_section(
                    document_id=doc.id,
                    heading=f"Level {level}",
                    body=f"Content at level {level}",
                    parent_section_id=parent_id,
                    order_index=0
                )
                parent_id = section.id
            elapsed = time.time() - start_time
            
            # Should be fast (< 1 second)
            assert elapsed < 1.0, f"Creating 10-level hierarchy took {elapsed:.2f}s"
            
            # Verify hierarchy
            tree = section_service.get_sections_by_document(doc.id, flat=False)
            assert len(tree) == 1
            
            # Navigate to deepest level
            current = tree[0]
            depth = 0
            while current.child_sections:
                current = current.child_sections[0]
                depth += 1
            assert depth == 9  # 10 levels total (0-9)

    def test_retrieve_deep_hierarchy(self, temp_db):
        """Test retrieving a deep hierarchy."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            doc = doc_service.create_document(title="Deep Document")
            
            # Create 15-level hierarchy
            parent_id = None
            for level in range(15):
                section = section_service.create_section(
                    document_id=doc.id,
                    heading=f"Level {level}",
                    body=f"Content {level}",
                    parent_section_id=parent_id,
                    order_index=0
                )
                parent_id = section.id
            
            # Measure retrieval time
            start_time = time.time()
            tree = section_service.get_sections_by_document(doc.id, flat=False)
            elapsed = time.time() - start_time
            
            # Should be fast (< 1 second)
            assert elapsed < 1.0, f"Retrieving 15-level hierarchy took {elapsed:.2f}s"

    def test_wide_hierarchy(self, temp_db):
        """Test performance with wide (many children) hierarchy."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            doc = doc_service.create_document(title="Wide Hierarchy Document")
            
            # Create parent with 100 children
            parent = section_service.create_section(
                document_id=doc.id,
                heading="Parent",
                body="Parent content"
            )
            
            start_time = time.time()
            for i in range(100):
                section_service.create_section(
                    document_id=doc.id,
                    heading=f"Child {i}",
                    body=f"Child content {i}",
                    parent_section_id=parent.id,
                    order_index=i
                )
            elapsed = time.time() - start_time
            
            # Should be fast (< 3 seconds)
            assert elapsed < 3.0, f"Creating 100 children took {elapsed:.2f}s"
            
            # Verify all children
            parent_retrieved = section_service.get_section(parent.id, include_children=True)
            assert len(parent_retrieved.child_sections) == 100


class TestFullTextSearchPerformance:
    """Test full-text search performance."""

    def test_search_large_corpus(self, temp_db):
        """Test searching across a large corpus of documents."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            # Create 10 documents with 20 sections each
            for doc_num in range(10):
                doc = doc_service.create_document(title=f"Document {doc_num}")
                for sec_num in range(20):
                    content = f"Python programming" if sec_num % 5 == 0 else f"Content {sec_num}"
                    section_service.create_section(
                        document_id=doc.id,
                        heading=f"Section {sec_num}",
                        body=content,
                        order_index=sec_num
                    )
            
            # Search across all documents
            start_time = time.time()
            results = section_service.search_sections("Python")
            elapsed = time.time() - start_time
            
            # Should be fast (< 2 seconds)
            assert elapsed < 2.0, f"Searching 200 sections took {elapsed:.2f}s"
            assert len(results) == 40  # 10 docs * 4 sections per doc

    def test_search_with_filters(self, temp_db):
        """Test search performance with metadata filters."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            # Create sections with metadata
            doc = doc_service.create_document(title="Filtered Search Document")
            for i in range(100):
                metadata = {
                    "category": "guide" if i % 2 == 0 else "tutorial",
                    "language": "python" if i % 3 == 0 else "javascript"
                }
                section_service.create_section(
                    document_id=doc.id,
                    heading=f"Section {i}",
                    body=f"Content {i}",
                    metadata=metadata,
                    order_index=i
                )
            
            # Filter and search
            start_time = time.time()
            sections = section_service.get_sections_by_document(
                doc.id,
                flat=True,
                metadata_filter={"category": "guide", "language": "python"}
            )
            elapsed = time.time() - start_time
            
            # Should be fast (< 1 second)
            assert elapsed < 1.0, f"Filtering 100 sections took {elapsed:.2f}s"
            assert len(sections) > 0


class TestConcurrentAccess:
    """Test concurrent access performance."""

    def test_concurrent_document_creation(self, temp_db):
        """Test creating documents concurrently."""
        def create_document(doc_num):
            with temp_db.session() as session:
                doc_service = DocumentService(session)
                return doc_service.create_document(title=f"Concurrent Document {doc_num}")
        
        # Create 20 documents concurrently
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_document, i) for i in range(20)]
            docs = [f.result() for f in futures]
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0, f"Creating 20 documents concurrently took {elapsed:.2f}s"
        assert len(docs) == 20
        assert len(set(d.id for d in docs)) == 20  # All unique

    def test_concurrent_section_creation(self, temp_db):
        """Test creating sections concurrently."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            doc = doc_service.create_document(title="Concurrent Sections Document")
        
        def create_section(sec_num):
            with temp_db.session() as session:
                section_service = SectionService(session)
                return section_service.create_section(
                    document_id=doc.id,
                    heading=f"Section {sec_num}",
                    body=f"Content {sec_num}",
                    order_index=sec_num
                )
        
        # Create 50 sections concurrently
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_section, i) for i in range(50)]
            sections = [f.result() for f in futures]
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 3 seconds)
        assert elapsed < 3.0, f"Creating 50 sections concurrently took {elapsed:.2f}s"
        assert len(sections) == 50

    def test_concurrent_reads(self, temp_db):
        """Test concurrent read operations."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            # Create document with sections
            doc = doc_service.create_document(title="Concurrent Read Document")
            for i in range(20):
                section_service.create_section(
                    document_id=doc.id,
                    heading=f"Section {i}",
                    body=f"Content {i}",
                    order_index=i
                )
        
        def read_document():
            with temp_db.session() as session:
                doc_service = DocumentService(session)
                return doc_service.get_document(doc.id, include_sections=True)
        
        # Read document 100 times concurrently
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(read_document) for _ in range(100)]
            results = [f.result() for f in futures]
        elapsed = time.time() - start_time
        
        # Should be fast (< 2 seconds)
        assert elapsed < 2.0, f"100 concurrent reads took {elapsed:.2f}s"
        assert len(results) == 100
        assert all(r.id == doc.id for r in results)

    def test_concurrent_updates(self, temp_db):
        """Test concurrent update operations."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            doc = doc_service.create_document(title="Concurrent Update Document")
        
        def update_document(version):
            with temp_db.session() as session:
                doc_service = DocumentService(session)
                return doc_service.update_document(
                    doc.id,
                    metadata={"version": version}
                )
        
        # Update document 10 times concurrently
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update_document, i) for i in range(10)]
            results = [f.result() for f in futures]
        elapsed = time.time() - start_time
        
        # Should complete (< 2 seconds)
        assert elapsed < 2.0, f"10 concurrent updates took {elapsed:.2f}s"
        assert len(results) == 10


class TestLargeDataHandling:
    """Test handling of large data volumes."""

    def test_large_section_body(self, temp_db):
        """Test creating sections with large body content."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            
            doc = doc_service.create_document(title="Large Content Document")
            
            # Create section with 100KB content
            large_content = "A" * (100 * 1024)
            
            start_time = time.time()
            section = section_service.create_section(
                document_id=doc.id,
                heading="Large Section",
                body=large_content
            )
            elapsed = time.time() - start_time
            
            # Should complete in reasonable time (< 2 seconds)
            assert elapsed < 2.0, f"Creating large section took {elapsed:.2f}s"
            
            # Verify content
            retrieved = section_service.get_section(section.id)
            assert len(retrieved.body) == 100 * 1024

    def test_many_links(self, temp_db):
        """Test creating many links for a section."""
        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)
            link_service = LinkService(session)
            
            doc = doc_service.create_document(title="Many Links Document")
            section = section_service.create_section(
                document_id=doc.id,
                heading="Section with Many Links",
                body="Content"
            )
            
            # Create 100 links
            start_time = time.time()
            for i in range(100):
                link_service.link_section(
                    section_id=section.id,
                    link_type="todo-rama",
                    link_target=f"todo-rama://task/{i}"
                )
            elapsed = time.time() - start_time
            
            # Should complete in reasonable time (< 3 seconds)
            assert elapsed < 3.0, f"Creating 100 links took {elapsed:.2f}s"
            
            # Verify links
            links = link_service.get_section_links(section.id)
            assert len(links) == 100
