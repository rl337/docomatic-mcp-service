"""Section service module with validation, tree operations, and reordering components."""

# Re-export submodules for direct access if needed
from docomatic.services.section.reordering import SectionReorderer
from docomatic.services.section.tree_operations import SectionTreeBuilder
from docomatic.services.section.validation import SectionValidator

__all__ = ["SectionValidator", "SectionTreeBuilder", "SectionReorderer"]
