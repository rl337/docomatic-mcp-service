"""MCP (Model Context Protocol) server for Doc-O-Matic.

This server exposes Doc-O-Matic functionality to AI agents via the Model Context Protocol.
It uses the standardized mcp library for JSON-RPC 2.0 communication over stdio.
"""

import asyncio
import logging

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import McpError
from mcp.types import ErrorData, TextContent

from docomatic.storage.database import get_db
from docomatic.mcp.tool_handlers import call_tool_handler
from docomatic.mcp.tool_schemas import get_tool_schemas

logger = logging.getLogger(__name__)

# Initialize MCP server
app = Server("doc-o-matic")


@app.list_tools()
async def list_tools() -> list:
    """List all available MCP tools."""
    return list(get_tool_schemas().values())


@app.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """Handle tool calls."""
    if arguments is None:
        arguments = {}

    db = get_db()

    try:
        # Call the async tool handler (handlers manage their own database sessions)
        return await call_tool_handler(name, arguments, db)
    except McpError:
        # Re-raise MCP errors as-is (handlers already convert exceptions to McpError)
        raise
    except Exception as e:
        # Fallback error handling for unexpected errors
        logger.exception(f"Unexpected error handling tool {name}")
        raise McpError(
            ErrorData(
                code=-32603,  # Internal error
                message=f"Internal error: {str(e)}",
            )
        )


async def main():
    """Main entry point for MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="doc-o-matic",
                server_version="0.1.0",
                capabilities={},
            ),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
