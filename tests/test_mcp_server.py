"""Integration tests for MCP server."""

import json
import tempfile
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from docomatic.mcp_server import MCPServer
from docomatic.storage.database import Database, reset_db


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Use temporary database
    database_url = f"sqlite:///{db_path}"
    reset_db()
    db = Database(database_url=database_url)
    db.create_tables()
    
    yield db
    
    # Cleanup
    reset_db()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def server(temp_db):
    """Create MCP server instance with temporary database."""
    # Create server and replace its db instance
    server = MCPServer()
    server.db = temp_db
    
    yield server


class TestMCPServer:
    """Test MCP server functionality."""

    def test_initialize(self, server):
        """Test server initialization."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        }
        response = server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert response["result"]["serverInfo"]["name"] == "doc-o-matic"

    def test_tools_list(self, server):
        """Test listing available tools."""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        response = server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 17
        
        # Check for key tools
        tool_names = [tool["name"] for tool in response["result"]["tools"]]
        assert "create_document" in tool_names
        assert "get_document" in tool_names
        assert "create_section" in tool_names
        assert "search_sections" in tool_names

    def test_create_document(self, server):
        """Test creating a document."""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "create_document",
                "arguments": {
                    "title": "Test Document",
                    "metadata": {"author": "Test Author"},
                },
            },
        }
        response = server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response
        assert "content" in response["result"]
        
        # Parse the result
        result_text = response["result"]["content"][0]["text"]
        result = json.loads(result_text)
        
        assert "id" in result
        assert result["title"] == "Test Document"
        assert result["metadata"]["author"] == "Test Author"

    def test_get_document(self, server):
        """Test retrieving a document."""
        # First create a document
        create_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "create_document",
                "arguments": {"title": "Test Document"},
            },
        }
        create_response = server.handle_request(create_request)
        create_result = json.loads(create_response["result"]["content"][0]["text"])
        document_id = create_result["id"]
        
        # Now get it
        get_request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "get_document",
                "arguments": {"document_id": document_id},
            },
        }
        get_response = server.handle_request(get_request)
        
        assert get_response["jsonrpc"] == "2.0"
        assert "result" in get_response
        
        result = json.loads(get_response["result"]["content"][0]["text"])
        assert result["id"] == document_id
        assert result["title"] == "Test Document"

    def test_create_section(self, server):
        """Test creating a section."""
        # First create a document
        create_doc_request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "create_document",
                "arguments": {"title": "Test Document"},
            },
        }
        create_doc_response = server.handle_request(create_doc_request)
        doc_result = json.loads(create_doc_response["result"]["content"][0]["text"])
        document_id = doc_result["id"]
        
        # Create a section
        create_section_request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "create_section",
                "arguments": {
                    "document_id": document_id,
                    "heading": "Introduction",
                    "body": "This is the introduction section.",
                },
            },
        }
        create_section_response = server.handle_request(create_section_request)
        
        assert create_section_response["jsonrpc"] == "2.0"
        assert "result" in create_section_response
        
        result = json.loads(create_section_response["result"]["content"][0]["text"])
        assert "id" in result
        assert result["heading"] == "Introduction"
        assert result["body"] == "This is the introduction section."
        assert result["document_id"] == document_id

    def test_search_sections(self, server):
        """Test searching sections."""
        # Create document and sections
        create_doc_request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "create_document",
                "arguments": {"title": "Test Document"},
            },
        }
        create_doc_response = server.handle_request(create_doc_request)
        doc_result = json.loads(create_doc_response["result"]["content"][0]["text"])
        document_id = doc_result["id"]
        
        # Create sections with searchable content
        for heading, body in [("Python", "Python programming"), ("Java", "Java programming")]:
            create_section_request = {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {
                    "name": "create_section",
                    "arguments": {
                        "document_id": document_id,
                        "heading": heading,
                        "body": body,
                    },
                },
            }
            server.handle_request(create_section_request)
        
        # Search for "Python"
        search_request = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "search_sections",
                "arguments": {"query": "Python"},
            },
        }
        search_response = server.handle_request(search_request)
        
        assert search_response["jsonrpc"] == "2.0"
        assert "result" in search_response
        
        result = json.loads(search_response["result"]["content"][0]["text"])
        assert "sections" in result
        assert len(result["sections"]) >= 1
        assert any("Python" in s["heading"] or "Python" in s["body"] for s in result["sections"])

    def test_link_section(self, server):
        """Test linking a section."""
        # Create document and section
        create_doc_request = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "create_document",
                "arguments": {"title": "Test Document"},
            },
        }
        create_doc_response = server.handle_request(create_doc_request)
        doc_result = json.loads(create_doc_response["result"]["content"][0]["text"])
        document_id = doc_result["id"]
        
        create_section_request = {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "create_section",
                "arguments": {
                    "document_id": document_id,
                    "heading": "Test Section",
                    "body": "Test body",
                },
            },
        }
        create_section_response = server.handle_request(create_section_request)
        section_result = json.loads(create_section_response["result"]["content"][0]["text"])
        section_id = section_result["id"]
        
        # Link section
        link_request = {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "link_section",
                "arguments": {
                    "section_id": section_id,
                    "link_type": "todo-rama",
                    "link_target": "todo-rama://task/123",
                },
            },
        }
        link_response = server.handle_request(link_request)
        
        assert link_response["jsonrpc"] == "2.0"
        assert "result" in link_response
        
        result = json.loads(link_response["result"]["content"][0]["text"])
        assert result["link_type"] == "todo-rama"
        assert result["link_target"] == "todo-rama://task/123"

    def test_validation_error(self, server):
        """Test validation error handling."""
        request = {
            "jsonrpc": "2.0",
            "id": 14,
            "method": "tools/call",
            "params": {
                "name": "create_document",
                "arguments": {"title": ""},  # Empty title should fail
            },
        }
        response = server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 14
        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params

    def test_not_found_error(self, server):
        """Test not found error handling."""
        request = {
            "jsonrpc": "2.0",
            "id": 15,
            "method": "tools/call",
            "params": {
                "name": "get_document",
                "arguments": {"document_id": "non-existent-id"},
            },
        }
        response = server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 15
        assert "error" in response
        assert response["error"]["code"] == -32001  # Not found

    def test_unknown_tool(self, server):
        """Test unknown tool error handling."""
        request = {
            "jsonrpc": "2.0",
            "id": 16,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {},
            },
        }
        response = server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 16
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found
