"""MCP module with tool schemas, handlers, and serializers."""

# Re-export for backward compatibility if needed
from docomatic.mcp.tool_handlers import call_tool_handler, TOOL_HANDLERS
from docomatic.mcp.tool_schemas import get_tool_schemas
from docomatic.mcp.serializers import serialize_model, serialize_section_tree

__all__ = [
    "call_tool_handler",
    "TOOL_HANDLERS",
    "get_tool_schemas",
    "serialize_model",
    "serialize_section_tree",
]
