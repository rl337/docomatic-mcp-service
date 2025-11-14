"""MCP tool handlers for executing tool operations."""

import json
from typing import Any

from mcp import McpError
from mcp.types import ErrorData, TextContent

from docomatic.config import get_settings
from docomatic.exceptions import (
    DatabaseError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from docomatic.services.document_service import DocumentService
from docomatic.services.export_service import (
    ExportConfig,
    ExportFormat,
    ExportService,
    GitHubAPIError,
    GitHubAuthenticationError,
)
from docomatic.services.link_service import LinkService
from docomatic.services.section_service import SectionService
from docomatic.mcp.serializers import serialize_model, serialize_section_tree


# Document handlers
async def handle_create_document(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle create_document tool."""
    with db.session() as session:
        doc_service = DocumentService(session)
        doc = doc_service.create_document(
            title=arguments["title"],
            metadata=arguments.get("metadata"),
            document_id=arguments.get("document_id"),
            initial_sections=arguments.get("initial_sections"),
        )
        result = serialize_model(doc)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_document(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle get_document tool."""
    with db.session() as session:
        doc_service = DocumentService(session)
        doc = doc_service.get_document(
            document_id=arguments["document_id"],
            include_sections=arguments.get("include_sections", True),
            include_links=arguments.get("include_links", True),
        )
        result = serialize_model(doc)
        if hasattr(doc, "sections") and doc.sections:
            result["sections"] = [
                serialize_section_tree(s) for s in doc.sections
            ]
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_update_document(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle update_document tool."""
    with db.session() as session:
        doc_service = DocumentService(session)
        doc = doc_service.update_document(
            document_id=arguments["document_id"],
            title=arguments.get("title"),
            metadata=arguments.get("metadata"),
        )
        result = serialize_model(doc)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_delete_document(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle delete_document tool."""
    with db.session() as session:
        doc_service = DocumentService(session)
        deleted = doc_service.delete_document(
            document_id=arguments["document_id"]
        )
        result = {"deleted": deleted}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_list_documents(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle list_documents tool."""
    with db.session() as session:
        doc_service = DocumentService(session)
        docs = doc_service.list_documents(
            title_pattern=arguments.get("title_pattern"),
            metadata_filter=arguments.get("metadata_filter"),
            limit=arguments.get("limit", 100),
            offset=arguments.get("offset", 0),
        )
        result = {"documents": docs}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


# Section handlers
async def handle_create_section(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle create_section tool."""
    with db.session() as session:
        section_service = SectionService(session)
        section = section_service.create_section(
            document_id=arguments["document_id"],
            heading=arguments["heading"],
            body=arguments["body"],
            parent_section_id=arguments.get("parent_section_id"),
            order_index=arguments.get("order_index", 0),
            metadata=arguments.get("metadata"),
            section_id=arguments.get("section_id"),
        )
        result = serialize_model(section)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_section(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle get_section tool."""
    with db.session() as session:
        section_service = SectionService(session)
        section = section_service.get_section(
            section_id=arguments["section_id"],
            include_children=arguments.get("include_children", True),
            include_links=arguments.get("include_links", True),
        )
        result = serialize_section_tree(section)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_update_section(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle update_section tool."""
    with db.session() as session:
        section_service = SectionService(session)
        section = section_service.update_section(
            section_id=arguments["section_id"],
            heading=arguments.get("heading"),
            body=arguments.get("body"),
            order_index=arguments.get("order_index"),
            metadata=arguments.get("metadata"),
        )
        result = serialize_model(section)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_delete_section(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle delete_section tool."""
    with db.session() as session:
        section_service = SectionService(session)
        deleted = section_service.delete_section(
            section_id=arguments["section_id"]
        )
        result = {"deleted": deleted}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_sections_by_document(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle get_sections_by_document tool."""
    with db.session() as session:
        section_service = SectionService(session)
        sections = section_service.get_sections_by_document(
            document_id=arguments["document_id"],
            flat=arguments.get("flat", False),
        )
        if arguments.get("flat", False):
            result = {"sections": [serialize_model(s) for s in sections]}
        else:
            result = {
                "sections": [
                    serialize_section_tree(s) for s in sections
                ]
            }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_search_sections(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle search_sections tool."""
    with db.session() as session:
        section_service = SectionService(session)
        sections = section_service.search_sections(
            query=arguments["query"],
            document_id=arguments.get("document_id"),
            limit=arguments.get("limit", 100),
        )
        result = {"sections": [serialize_model(s) for s in sections]}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


# Link handlers
async def handle_link_section(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle link_section tool."""
    with db.session() as session:
        link_service = LinkService(session)
        link = link_service.link_section(
            section_id=arguments["section_id"],
            link_type=arguments["link_type"],
            link_target=arguments["link_target"],
            link_metadata=arguments.get("link_metadata"),
            link_id=arguments.get("link_id"),
        )
        result = serialize_model(link)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_unlink_section(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle unlink_section tool."""
    with db.session() as session:
        link_service = LinkService(session)
        deleted = link_service.unlink_section(link_id=arguments["link_id"])
        result = {"deleted": deleted}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_section_links(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle get_section_links tool."""
    with db.session() as session:
        link_service = LinkService(session)
        links = link_service.get_section_links(
            section_id=arguments["section_id"]
        )
        result = {"links": [serialize_model(link) for link in links]}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_sections_by_link(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle get_sections_by_link tool."""
    with db.session() as session:
        link_service = LinkService(session)
        sections = link_service.get_sections_by_link(
            link_type=arguments["link_type"],
            link_target=arguments["link_target"],
        )
        result = {"sections": sections}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_link_document(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle link_document tool."""
    with db.session() as session:
        link_service = LinkService(session)
        link = link_service.link_document(
            document_id=arguments["document_id"],
            link_type=arguments["link_type"],
            link_target=arguments["link_target"],
            link_metadata=arguments.get("link_metadata"),
            link_id=arguments.get("link_id"),
        )
        result = serialize_model(link)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_unlink_document(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle unlink_document tool."""
    with db.session() as session:
        link_service = LinkService(session)
        deleted = link_service.unlink_document(link_id=arguments["link_id"])
        result = {"deleted": deleted}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_document_links(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle get_document_links tool."""
    with db.session() as session:
        link_service = LinkService(session)
        links = link_service.get_document_links(
            document_id=arguments["document_id"]
        )
        result = {"links": [serialize_model(link) for link in links]}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_documents_by_link(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle get_documents_by_link tool."""
    with db.session() as session:
        link_service = LinkService(session)
        documents = link_service.get_documents_by_link(
            link_type=arguments["link_type"],
            link_target=arguments["link_target"],
        )
        result = {"documents": documents}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_links_by_type(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle get_links_by_type tool."""
    with db.session() as session:
        link_service = LinkService(session)
        links = link_service.get_links_by_type(
            link_type=arguments["link_type"],
            limit=arguments.get("limit", 100),
        )
        result = {"links": [serialize_model(link) for link in links]}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_update_link_metadata(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle update_link_metadata tool."""
    with db.session() as session:
        link_service = LinkService(session)
        link = link_service.update_link_metadata(
            link_id=arguments["link_id"],
            link_metadata=arguments["link_metadata"],
        )
        result = serialize_model(link)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_generate_link_report(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle generate_link_report tool."""
    with db.session() as session:
        link_service = LinkService(session)
        report = link_service.generate_link_report(
            document_id=arguments.get("document_id"),
            link_type=arguments.get("link_type"),
        )
        return [TextContent(type="text", text=json.dumps(report, indent=2))]


# Export handlers
async def handle_export_to_github(arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """Handle export_to_github tool."""
    # Get GitHub token from arguments or settings
    github_token = arguments.get("github_token") or get_settings().get_github_token()
    if not github_token:
        raise McpError(
            ErrorData(
                code=-32602,  # Invalid params
                message="GitHub token is required. Provide github_token parameter or set GITHUB_TOKEN environment variable.",
            )
        )

    with db.session() as session:
        # Build export configuration
        export_format = ExportFormat.SINGLE_FILE
        if arguments.get("format") == "multi":
            export_format = ExportFormat.MULTI_FILE

        config = ExportConfig(
            format=export_format,
            file_naming=arguments.get("file_naming", "kebab-case"),
            directory_structure=arguments.get("directory_structure", "flat"),
            include_metadata=arguments.get("include_metadata", True),
            convert_internal_links=arguments.get("convert_internal_links", True),
            preserve_external_links=arguments.get("preserve_external_links", True),
            base_path=arguments.get("base_path", "docs"),
            branch=arguments.get("branch"),
        )

        # Export document
        export_service = ExportService(session, github_token)
        result = export_service.export_document(
            document_id=arguments["document_id"],
            repo_owner=arguments["repo_owner"],
            repo_name=arguments["repo_name"],
            config=config,
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


# Tool handler registry
TOOL_HANDLERS: dict[str, callable] = {
    "create_document": handle_create_document,
    "get_document": handle_get_document,
    "update_document": handle_update_document,
    "delete_document": handle_delete_document,
    "list_documents": handle_list_documents,
    "create_section": handle_create_section,
    "get_section": handle_get_section,
    "update_section": handle_update_section,
    "delete_section": handle_delete_section,
    "get_sections_by_document": handle_get_sections_by_document,
    "search_sections": handle_search_sections,
    "link_section": handle_link_section,
    "unlink_section": handle_unlink_section,
    "get_section_links": handle_get_section_links,
    "get_sections_by_link": handle_get_sections_by_link,
    "link_document": handle_link_document,
    "unlink_document": handle_unlink_document,
    "get_document_links": handle_get_document_links,
    "get_documents_by_link": handle_get_documents_by_link,
    "get_links_by_type": handle_get_links_by_type,
    "update_link_metadata": handle_update_link_metadata,
    "generate_link_report": handle_generate_link_report,
    "export_to_github": handle_export_to_github,
}


async def call_tool_handler(tool_name: str, arguments: dict[str, Any], db: Any) -> list[TextContent]:
    """
    Call the appropriate tool handler.

    Args:
        tool_name: Name of the tool to call
        arguments: Tool arguments
        db: Database instance

    Returns:
        List of TextContent with tool execution result

    Raises:
        McpError: If tool name is unknown or handler raises an error
    """
    if tool_name not in TOOL_HANDLERS:
        raise McpError(
            ErrorData(
                code=-32601,  # Method not found
                message=f"Unknown tool: {tool_name}",
            )
        )
    
    handler = TOOL_HANDLERS[tool_name]
    
    try:
        return await handler(arguments, db)
    except McpError:
        # Re-raise MCP errors as-is
        raise
    except ValidationError as e:
        raise McpError(
            ErrorData(
                code=-32602,  # Invalid params
                message=f"Validation error: {str(e)}",
            )
        )
    except NotFoundError as e:
        raise McpError(
            ErrorData(
                code=-32001,  # Custom error: not found
                message=str(e),
            )
        )
    except DuplicateError as e:
        raise McpError(
            ErrorData(
                code=-32002,  # Custom error: duplicate
                message=str(e),
            )
        )
    except DatabaseError as e:
        raise McpError(
            ErrorData(
                code=-32603,  # Internal error
                message=f"Database error: {str(e)}",
            )
        )
    except GitHubAuthenticationError as e:
        raise McpError(
            ErrorData(
                code=-32603,  # Internal error
                message=f"GitHub authentication error: {str(e)}",
            )
        )
    except GitHubAPIError as e:
        raise McpError(
            ErrorData(
                code=-32603,  # Internal error
                message=f"GitHub API error: {str(e)}",
            )
        )
    except Exception as e:
        raise McpError(
            ErrorData(
                code=-32603,  # Internal error
                message=f"Internal error: {str(e)}",
            )
        )
