"""Section validation logic."""

from typing import Any

from docomatic.exceptions import ValidationError


class SectionValidator:
    """Validates section data according to business rules."""

    # Validation constants
    HEADING_MIN_LENGTH = 1
    HEADING_MAX_LENGTH = 500
    ID_MAX_LENGTH = 255

    @staticmethod
    def validate_heading(heading: str) -> None:
        """
        Validate section heading.

        Args:
            heading: Heading to validate

        Raises:
            ValidationError: If heading is invalid
        """
        if not isinstance(heading, str):
            raise ValidationError("Heading must be a string", "heading")
        if not heading or not heading.strip():
            raise ValidationError("Heading is required and cannot be empty", "heading")
        if len(heading) < SectionValidator.HEADING_MIN_LENGTH:
            raise ValidationError(
                f"Heading must be at least {SectionValidator.HEADING_MIN_LENGTH} character(s)", "heading"
            )
        if len(heading) > SectionValidator.HEADING_MAX_LENGTH:
            raise ValidationError(
                f"Heading must be at most {SectionValidator.HEADING_MAX_LENGTH} characters", "heading"
            )

    @staticmethod
    def validate_id(section_id: str) -> None:
        """
        Validate section ID.

        Args:
            section_id: Section ID to validate

        Raises:
            ValidationError: If section_id is invalid
        """
        if not isinstance(section_id, str):
            raise ValidationError("Section ID must be a string", "id")
        if not section_id or not section_id.strip():
            raise ValidationError("Section ID cannot be empty", "id")
        if len(section_id) > SectionValidator.ID_MAX_LENGTH:
            raise ValidationError(
                f"Section ID must be at most {SectionValidator.ID_MAX_LENGTH} characters", "id"
            )

    @staticmethod
    def validate_metadata(metadata: dict[str, Any]) -> None:
        """
        Validate metadata structure.

        Args:
            metadata: Metadata dictionary to validate

        Raises:
            ValidationError: If metadata is invalid
        """
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a dictionary", "metadata")

    @staticmethod
    def validate_body(body: str) -> None:
        """
        Validate section body.

        Args:
            body: Body to validate

        Raises:
            ValidationError: If body is invalid
        """
        if not isinstance(body, str):
            raise ValidationError("Body must be a string", "body")
