"""Link validation logic."""

import re
from typing import Any

from docomatic.exceptions import ValidationError


class LinkValidator:
    """Validates link data according to business rules."""

    # Validation constants
    LINK_TYPE_MAX_LENGTH = 50
    LINK_TARGET_MAX_LENGTH = 500
    ID_MAX_LENGTH = 255
    VALID_LINK_TYPES = {"todo-rama", "bucket-o-facts", "github"}

    @staticmethod
    def validate_id(link_id: str) -> None:
        """
        Validate link ID.

        Args:
            link_id: Link ID to validate

        Raises:
            ValidationError: If link_id is invalid
        """
        if not isinstance(link_id, str):
            raise ValidationError("Link ID must be a string", "id")
        if not link_id or not link_id.strip():
            raise ValidationError("Link ID cannot be empty", "id")
        if len(link_id) > LinkValidator.ID_MAX_LENGTH:
            raise ValidationError(
                f"Link ID must be at most {LinkValidator.ID_MAX_LENGTH} characters", "id"
            )

    @staticmethod
    def validate_link_type(link_type: str) -> None:
        """
        Validate link type.

        Args:
            link_type: Link type to validate

        Raises:
            ValidationError: If link_type is invalid
        """
        if not isinstance(link_type, str):
            raise ValidationError("Link type must be a string", "link_type")
        if not link_type or not link_type.strip():
            raise ValidationError("Link type is required and cannot be empty", "link_type")
        if len(link_type) > LinkValidator.LINK_TYPE_MAX_LENGTH:
            raise ValidationError(
                f"Link type must be at most {LinkValidator.LINK_TYPE_MAX_LENGTH} characters",
                "link_type",
            )
        if link_type not in LinkValidator.VALID_LINK_TYPES:
            raise ValidationError(
                f"Link type must be one of: {', '.join(LinkValidator.VALID_LINK_TYPES)}",
                "link_type",
            )

    @staticmethod
    def validate_link_target(link_target: str) -> None:
        """
        Validate link target.

        Args:
            link_target: Link target to validate

        Raises:
            ValidationError: If link_target is invalid
        """
        if not isinstance(link_target, str):
            raise ValidationError("Link target must be a string", "link_target")
        if not link_target or not link_target.strip():
            raise ValidationError(
                "Link target is required and cannot be empty", "link_target"
            )
        if len(link_target) > LinkValidator.LINK_TARGET_MAX_LENGTH:
            raise ValidationError(
                f"Link target must be at most {LinkValidator.LINK_TARGET_MAX_LENGTH} characters",
                "link_target",
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
    def validate_link_target_format(link_type: str, link_target: str) -> None:
        """
        Validate link target format based on link type.

        Args:
            link_type: Link type ('todo-rama', 'bucket-o-facts', or 'github')
            link_target: Link target to validate

        Raises:
            ValidationError: If link target format is invalid
        """
        if link_type == "todo-rama":
            # Format: todo-rama://project/task/<task_id> or todo-rama://task/<task_id>
            pattern = r"^todo-rama://(project/task/|task/)[a-zA-Z0-9_-]+$"
            if not re.match(pattern, link_target):
                raise ValidationError(
                    "Todo-Rama link target must match format: "
                    "todo-rama://project/task/<task_id> or todo-rama://task/<task_id>",
                    "link_target",
                )
        elif link_type == "bucket-o-facts":
            # Format: bucket-o-facts://fact/<fact_id>
            pattern = r"^bucket-o-facts://fact/[a-zA-Z0-9_-]+$"
            if not re.match(pattern, link_target):
                raise ValidationError(
                    "Bucket-O-Facts link target must match format: "
                    "bucket-o-facts://fact/<fact_id>",
                    "link_target",
                )
        elif link_type == "github":
            # Format: github://owner/repo/commit/<sha> or github://owner/repo/pull/<number>
            # or github://owner/repo/issues/<number> or github://owner/repo/blob/<path>
            pattern = (
                r"^github://[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+/"
                r"(commit/[a-f0-9]+|pull/\d+|issues/\d+|blob/[a-zA-Z0-9_./-]+)$"
            )
            if not re.match(pattern, link_target):
                raise ValidationError(
                    "GitHub link target must match format: "
                    "github://owner/repo/commit/<sha>, "
                    "github://owner/repo/pull/<number>, "
                    "github://owner/repo/issues/<number>, or "
                    "github://owner/repo/blob/<path>",
                    "link_target",
                )
