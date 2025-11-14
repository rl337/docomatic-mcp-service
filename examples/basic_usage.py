"""Basic usage example for Doc-O-Matic database schema."""

import os
import uuid

from docomatic.models.document import Document
from docomatic.models.link import Link
from docomatic.models.section import Section
from docomatic.storage import Database, DocumentRepository, LinkRepository, SectionRepository


def main():
    """Demonstrate basic database operations."""
    # Initialize database (uses SQLite by default)
    db = Database()

    # Create tables
    db.create_tables()

    # Create a document with sections
    with db.session() as session:
        # Create repositories
        doc_repo = DocumentRepository(session)
        section_repo = SectionRepository(session)
        link_repo = LinkRepository(session)

        # Create a document
        doc = Document(
            id=str(uuid.uuid4()),
            title="Getting Started Guide",
            metadata={"version": "1.0", "author": "Doc-O-Matic"},
        )
        doc = doc_repo.create(doc)
        print(f"Created document: {doc.title} (ID: {doc.id})")

        # Create top-level section
        section1 = Section(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            heading="Introduction",
            body="This is the introduction section.",
            order_index=0,
            metadata={"last_modified_by": "admin"},
        )
        section1 = section_repo.create(section1)
        print(f"Created section: {section1.heading}")

        # Create nested section
        section2 = Section(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            parent_section_id=section1.id,
            heading="Overview",
            body="This is a nested section.",
            order_index=0,
        )
        section2 = section_repo.create(section2)
        print(f"Created nested section: {section2.heading}")

        # Create a link to a To-Do-Rama task
        link = Link(
            id=str(uuid.uuid4()),
            section_id=section1.id,
            link_type="todo-rama",
            link_target="task-123",
            link_metadata={"title": "Implement feature X", "url": "todo-rama://task-123"},
        )
        link = link_repo.create(link)
        print(f"Created link: {link.link_type} -> {link.link_target}")

        # Query operations
        print("\n--- Query Examples ---")

        # Get document with sections
        doc_with_sections = doc_repo.get_by_id_with_sections(doc.id)
        print(f"Document has {len(doc_with_sections.sections)} sections")

        # Get section tree
        tree = section_repo.get_section_tree_by_document(doc.id)
        print(f"Document has {len(tree)} top-level sections")
        for section in tree:
            print(f"  - {section.heading} ({len(section.child_sections)} children)")

        # Search sections
        results = section_repo.search_by_heading("Intro", document_id=doc.id)
        print(f"Found {len(results)} sections matching 'Intro'")

        # Get links
        links = link_repo.get_by_section_id(section1.id)
        print(f"Section has {len(links)} links")

    print("\n✅ All operations completed successfully!")


if __name__ == "__main__":
    main()
