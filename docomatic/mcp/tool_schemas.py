"""MCP tool schema definitions."""

from typing import Any


def get_tool_schemas() -> dict[str, dict[str, Any]]:
    """Get all MCP tool schemas."""
    return {
        "create_document": {
            "name": "create_document",
            "description": "Create a new document with title and optional initial sections",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "metadata": {
                        "type": "object",
                        "description": "Optional document metadata",
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Optional document ID (generates UUID if not provided)",
                    },
                    "initial_sections": {
                        "type": "array",
                        "description": "Optional list of initial sections",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {"type": "string"},
                                "body": {"type": "string"},
                                "order_index": {"type": "integer"},
                                "parent_section_id": {"type": "string"},
                                "metadata": {"type": "object"},
                            },
                            "required": ["heading", "body"],
                        },
                    },
                },
                "required": ["title"],
            },
        },
        "get_document": {
            "name": "get_document",
            "description": "Retrieve a document by ID with all sections (tree structure)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Document ID"},
                    "include_sections": {
                        "type": "boolean",
                        "description": "Include sections in response (default: true)",
                    },
                    "include_links": {
                        "type": "boolean",
                        "description": "Include links in response (default: true)",
                    },
                },
                "required": ["document_id"],
            },
        },
        "update_document": {
            "name": "update_document",
            "description": "Update document title or metadata",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Document ID"},
                    "title": {"type": "string", "description": "New title"},
                    "metadata": {
                        "type": "object",
                        "description": "New metadata (replaces existing)",
                    },
                },
                "required": ["document_id"],
            },
        },
        "delete_document": {
            "name": "delete_document",
            "description": "Delete a document and all its sections",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Document ID"},
                },
                "required": ["document_id"],
            },
        },
        "list_documents": {
            "name": "list_documents",
            "description": "List all documents with optional filtering",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title_pattern": {
                        "type": "string",
                        "description": "Optional title pattern to filter by",
                    },
                    "metadata_filter": {
                        "type": "object",
                        "description": "Optional metadata filter",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents (default: 100)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of documents to skip (default: 0)",
                    },
                },
            },
        },
        "create_section": {
            "name": "create_section",
            "description": "Create a new section in a document (with parent for nesting)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Document ID"},
                    "heading": {"type": "string", "description": "Section heading"},
                    "body": {"type": "string", "description": "Section body content"},
                    "parent_section_id": {
                        "type": "string",
                        "description": "Optional parent section ID for nesting",
                    },
                    "order_index": {
                        "type": "integer",
                        "description": "Order within parent (default: 0)",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional section metadata",
                    },
                    "section_id": {
                        "type": "string",
                        "description": "Optional section ID (generates UUID if not provided)",
                    },
                },
                "required": ["document_id", "heading", "body"],
            },
        },
        "get_section": {
            "name": "get_section",
            "description": "Retrieve a section by ID with children",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"},
                    "include_children": {
                        "type": "boolean",
                        "description": "Include children in response (default: true)",
                    },
                    "include_links": {
                        "type": "boolean",
                        "description": "Include links in response (default: true)",
                    },
                },
                "required": ["section_id"],
            },
        },
        "update_section": {
            "name": "update_section",
            "description": "Update section heading, body, or metadata",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"},
                    "heading": {"type": "string", "description": "New heading"},
                    "body": {"type": "string", "description": "New body"},
                    "order_index": {
                        "type": "integer",
                        "description": "New order index",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "New metadata (replaces existing)",
                    },
                },
                "required": ["section_id"],
            },
        },
        "delete_section": {
            "name": "delete_section",
            "description": "Delete a section and its children",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"},
                },
                "required": ["section_id"],
            },
        },
        "get_sections_by_document": {
            "name": "get_sections_by_document",
            "description": "Get all sections for a document (tree or flat)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Document ID"},
                    "flat": {
                        "type": "boolean",
                        "description": "Return flat list instead of tree (default: false)",
                    },
                },
                "required": ["document_id"],
            },
        },
        "search_sections": {
            "name": "search_sections",
            "description": "Full-text search across section headings and bodies",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Optional document ID to limit search",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 100)",
                    },
                },
                "required": ["query"],
            },
        },
        "link_section": {
            "name": "link_section",
            "description": "Link a section to To-Do-Rama task, Bucket-O-Facts fact, or GitHub resource",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"},
                    "link_type": {
                        "type": "string",
                        "enum": ["todo-rama", "bucket-o-facts", "github"],
                        "description": "Link type",
                    },
                    "link_target": {
                        "type": "string",
                        "description": "Link target (URI or identifier)",
                    },
                    "link_metadata": {
                        "type": "object",
                        "description": "Optional link metadata",
                    },
                    "link_id": {
                        "type": "string",
                        "description": "Optional link ID (generates UUID if not provided)",
                    },
                },
                "required": ["section_id", "link_type", "link_target"],
            },
        },
        "unlink_section": {
            "name": "unlink_section",
            "description": "Remove a link from a section",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "link_id": {"type": "string", "description": "Link ID"},
                },
                "required": ["link_id"],
            },
        },
        "get_section_links": {
            "name": "get_section_links",
            "description": "Get all links for a section",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"},
                },
                "required": ["section_id"],
            },
        },
        "get_sections_by_link": {
            "name": "get_sections_by_link",
            "description": "Find all sections linked to a specific task/fact/GitHub resource",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "link_type": {
                        "type": "string",
                        "enum": ["todo-rama", "bucket-o-facts", "github"],
                        "description": "Link type",
                    },
                    "link_target": {
                        "type": "string",
                        "description": "Link target (URI or identifier)",
                    },
                },
                "required": ["link_type", "link_target"],
            },
        },
        "link_document": {
            "name": "link_document",
            "description": "Link a document to To-Do-Rama task, Bucket-O-Facts fact, or GitHub resource",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Document ID"},
                    "link_type": {
                        "type": "string",
                        "enum": ["todo-rama", "bucket-o-facts", "github"],
                        "description": "Link type",
                    },
                    "link_target": {
                        "type": "string",
                        "description": "Link target (URI or identifier)",
                    },
                    "link_metadata": {
                        "type": "object",
                        "description": "Optional link metadata",
                    },
                    "link_id": {
                        "type": "string",
                        "description": "Optional link ID (generates UUID if not provided)",
                    },
                },
                "required": ["document_id", "link_type", "link_target"],
            },
        },
        "unlink_document": {
            "name": "unlink_document",
            "description": "Remove a link from a document",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "link_id": {"type": "string", "description": "Link ID"},
                },
                "required": ["link_id"],
            },
        },
        "get_document_links": {
            "name": "get_document_links",
            "description": "Get all links for a document",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Document ID"},
                },
                "required": ["document_id"],
            },
        },
        "get_documents_by_link": {
            "name": "get_documents_by_link",
            "description": "Find all documents linked to a specific task/fact/GitHub resource",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "link_type": {
                        "type": "string",
                        "enum": ["todo-rama", "bucket-o-facts", "github"],
                        "description": "Link type",
                    },
                    "link_target": {
                        "type": "string",
                        "description": "Link target (URI or identifier)",
                    },
                },
                "required": ["link_type", "link_target"],
            },
        },
        "get_links_by_type": {
            "name": "get_links_by_type",
            "description": "Get all links of a specific type",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "link_type": {
                        "type": "string",
                        "enum": ["todo-rama", "bucket-o-facts", "github"],
                        "description": "Link type",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of links to return (default: 100)",
                    },
                },
                "required": ["link_type"],
            },
        },
        "update_link_metadata": {
            "name": "update_link_metadata",
            "description": "Update link metadata",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "link_id": {"type": "string", "description": "Link ID"},
                    "link_metadata": {
                        "type": "object",
                        "description": "New link metadata",
                    },
                },
                "required": ["link_id", "link_metadata"],
            },
        },
        "generate_link_report": {
            "name": "generate_link_report",
            "description": "Generate a comprehensive link report with statistics",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Optional document ID to filter by",
                    },
                    "link_type": {
                        "type": "string",
                        "enum": ["todo-rama", "bucket-o-facts", "github"],
                        "description": "Optional link type to filter by",
                    },
                },
            },
        },
        "export_to_github": {
            "name": "export_to_github",
            "description": "Export a document to GitHub as Markdown file(s)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Document ID"},
                    "repo_owner": {"type": "string", "description": "GitHub repository owner"},
                    "repo_name": {"type": "string", "description": "GitHub repository name"},
                    "format": {
                        "type": "string",
                        "enum": ["single", "multi"],
                        "description": "Export format: single file or one file per section (default: single)",
                    },
                    "file_naming": {
                        "type": "string",
                        "enum": ["kebab-case", "snake_case", "preserve"],
                        "description": "File naming convention (default: kebab-case)",
                    },
                    "directory_structure": {
                        "type": "string",
                        "enum": ["flat", "hierarchical"],
                        "description": "Directory structure for multi-file exports (default: flat)",
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "Include metadata in frontmatter (default: true)",
                    },
                    "base_path": {
                        "type": "string",
                        "description": "Base directory path in repository (default: docs)",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Optional branch name (creates if doesn't exist)",
                    },
                    "github_token": {
                        "type": "string",
                        "description": "GitHub personal access token (optional, uses GITHUB_TOKEN env var if not provided)",
                    },
                },
                "required": ["document_id", "repo_owner", "repo_name"],
            },
        },
    }
