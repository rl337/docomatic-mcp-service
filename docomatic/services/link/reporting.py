"""Link reporting logic."""

from typing import Any

from docomatic.exceptions import DatabaseError, NotFoundError, ValidationError
from docomatic.storage.repositories import LinkRepository


class LinkReporter:
    """Generates link reports and statistics."""

    def __init__(self, link_repo: LinkRepository):
        """
        Initialize link reporter with repository.

        Args:
            link_repo: Link repository for data access
        """
        self.link_repo = link_repo

    def generate_link_report(
        self, document_id: str | None = None, link_type: str | None = None
    ) -> dict[str, Any]:
        """
        Generate a comprehensive link report.

        Args:
            document_id: Optional document ID to filter by
            link_type: Optional link type to filter by

        Returns:
            Dictionary containing link statistics and breakdown

        Raises:
            ValidationError: If document_id or link_type is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Get all links (filtered if needed)
            if document_id:
                from docomatic.services.link.validation import LinkValidator

                LinkValidator.validate_id(document_id)
                links = self.link_repo.get_by_document_id(document_id)
            elif link_type:
                from docomatic.services.link.validation import LinkValidator

                LinkValidator.validate_link_type(link_type)
                links = self.link_repo.get_by_link_type(link_type, limit=10000)
            else:
                # Get all links (we'll need to add a method for this)
                # For now, get by each type
                from docomatic.services.link.validation import LinkValidator

                all_links = []
                for lt in LinkValidator.VALID_LINK_TYPES:
                    all_links.extend(self.link_repo.get_by_link_type(lt, limit=10000))
                links = all_links

            # Generate statistics
            total_links = len(links)
            by_type = {}
            by_target = {}
            section_links = 0
            document_links = 0

            for link in links:
                # Count by type
                by_type[link.link_type] = by_type.get(link.link_type, 0) + 1

                # Count by target (top 10)
                target_key = f"{link.link_type}:{link.link_target}"
                by_target[target_key] = by_target.get(target_key, 0) + 1

                # Count section vs document links
                if link.section_id:
                    section_links += 1
                elif link.document_id:
                    document_links += 1

            # Get top targets
            top_targets = sorted(
                by_target.items(), key=lambda x: x[1], reverse=True
            )[:10]

            return {
                "total_links": total_links,
                "by_type": by_type,
                "section_links": section_links,
                "document_links": document_links,
                "top_targets": [
                    {"target": target, "count": count}
                    for target, count in top_targets
                ],
            }

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            raise DatabaseError(
                f"Failed to generate link report: {str(e)}", e
            ) from e
