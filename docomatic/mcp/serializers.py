"""Model serialization for MCP responses."""

from typing import Any


def serialize_model(obj: Any) -> dict[str, Any]:
    """
    Serialize a SQLAlchemy model to dictionary.

    Args:
        obj: SQLAlchemy model instance

    Returns:
        Dictionary representation of the model
    """
    if hasattr(obj, "__dict__"):
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith("_"):
                # Map 'meta' attribute back to 'metadata' for API compatibility
                # (SQLAlchemy reserves 'metadata' as a name, so we use 'meta' internally)
                output_key = "metadata" if key == "meta" else key
                
                if hasattr(value, "isoformat"):  # datetime
                    result[output_key] = value.isoformat()
                elif isinstance(value, dict):
                    result[output_key] = value
                elif isinstance(value, list):
                    result[output_key] = [
                        serialize_model(item) if hasattr(item, "__dict__") else item
                        for item in value
                    ]
                else:
                    result[output_key] = value
        return result
    return obj


def serialize_section_tree(section: Any) -> dict[str, Any]:
    """
    Serialize section with children recursively.

    Args:
        section: Section model instance

    Returns:
        Dictionary representation of section with nested children
    """
    result = serialize_model(section)
    if hasattr(section, "child_sections") and section.child_sections:
        result["children"] = [
            serialize_section_tree(child) for child in section.child_sections
        ]
    return result
