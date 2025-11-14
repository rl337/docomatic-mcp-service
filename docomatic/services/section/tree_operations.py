"""Section tree operations."""

from typing import Any

from docomatic.models.section import Section
from docomatic.storage.repositories import SectionRepository


class SectionTreeBuilder:
    """Builds and manipulates section tree structures."""

    def __init__(self, section_repo: SectionRepository):
        """
        Initialize tree builder with repository.

        Args:
            section_repo: Section repository for data access
        """
        self.section_repo = section_repo

    def build_tree_with_filters(
        self,
        document_id: str,
        flat: bool = False,
        heading_pattern: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[Section]:
        """
        Get all sections for a document with optional filtering.

        Args:
            document_id: Document ID
            flat: If True, return flat list. If False, return tree structure.
            heading_pattern: Optional heading pattern to filter by (case-insensitive substring match)
            metadata_filter: Optional metadata filter (checks if metadata contains all key-value pairs)

        Returns:
            List of sections (tree or flat)
        """
        if flat:
            sections = self.section_repo.get_by_document_id(document_id, flat=True)
        else:
            sections = self.section_repo.get_section_tree_by_document(document_id)

        # Apply heading pattern filter
        if heading_pattern:
            sections = [
                s for s in sections
                if heading_pattern.lower() in s.heading.lower()
            ]

        # Apply metadata filter
        if metadata_filter:
            filtered_sections = []
            for section in sections:
                if self._matches_metadata_filter(section, metadata_filter):
                    filtered_sections.append(section)
            sections = filtered_sections

        return sections

    @staticmethod
    def matches_metadata_filter(section: Section, metadata_filter: dict[str, Any]) -> bool:
        """
        Check if section metadata matches the filter.

        Args:
            section: Section to check
            metadata_filter: Dictionary of key-value pairs to match

        Returns:
            True if all filter key-value pairs exist in section metadata
        """
        if not section.meta:
            return False

        for key, value in metadata_filter.items():
            if key not in section.meta:
                return False
            if section.meta[key] != value:
                return False

        return True

    def _matches_metadata_filter(self, section: Section, metadata_filter: dict[str, Any]) -> bool:
        """Instance method wrapper for static method."""
        return self.matches_metadata_filter(section, metadata_filter)

    def would_create_cycle(self, section_id: str, new_parent_id: str | None) -> bool:
        """
        Check if moving section to new_parent would create a cycle.

        Args:
            section_id: Section ID to move
            new_parent_id: Potential new parent ID

        Returns:
            True if cycle would be created, False otherwise
        """
        # If moving to None (top-level), no cycle possible
        if new_parent_id is None:
            return False

        # If new parent is the section itself, that's a cycle
        if section_id == new_parent_id:
            return True

        # Check if new_parent is a descendant of section (would create cycle)
        # Get all descendants of section by traversing the tree
        def get_all_descendant_ids(node_id: str, visited: set[str]) -> set[str]:
            """Recursively get all descendant IDs."""
            descendants = set()
            children = self.section_repo.get_children(node_id)
            for child in children:
                if child.id in visited:
                    # Cycle detected in tree structure (shouldn't happen, but be safe)
                    continue
                visited.add(child.id)
                descendants.add(child.id)
                # Recursively get descendants of this child
                descendants.update(get_all_descendant_ids(child.id, visited))
            return descendants

        # Get all descendants of the section we're trying to move
        all_descendants = get_all_descendant_ids(section_id, {section_id})
        
        # If new_parent_id is in the descendants, it would create a cycle
        return new_parent_id in all_descendants
