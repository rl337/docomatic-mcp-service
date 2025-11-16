"""HTTP API for Doc-O-Matic MCP service using Server-Sent Events (SSE)."""

import json
import logging
from typing import Any, Dict

from fastapi import FastAPI, Body, Request
from fastapi.responses import StreamingResponse
from mcp.types import TextContent

from docomatic.storage.database import get_db
from docomatic.mcp.tool_handlers import call_tool_handler
from docomatic.mcp.tool_schemas import get_tool_schemas

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Doc-O-Matic MCP Service",
    description="Structured documentation system for AI agents",
    version="0.1.0",
)


async def handle_jsonrpc_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle JSON-RPC 2.0 request."""
    jsonrpc = request.get("jsonrpc", "2.0")
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": jsonrpc,
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {
                    "name": "doc-o-matic",
                    "version": "0.1.0"
                }
            }
        }
    elif method == "tools/list":
        # Return list of available tools
        tool_schemas = get_tool_schemas()
        tools = []
        for tool_name, tool_def in tool_schemas.items():
            tools.append({
                "name": tool_def["name"],
                "description": tool_def["description"],
                "inputSchema": tool_def["inputSchema"]
            })
        return {
            "jsonrpc": jsonrpc,
            "id": request_id,
            "result": {
                "tools": tools
            }
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            db = get_db()
            result = await call_tool_handler(tool_name, arguments, db)
            
            # Convert TextContent list to JSON string
            if isinstance(result, list) and result and isinstance(result[0], TextContent):
                result_text = result[0].text
            else:
                result_text = json.dumps(result) if not isinstance(result, str) else result

            return {
                "jsonrpc": jsonrpc,
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
            }
        except Exception as e:
            logger.exception(f"Error handling tool {tool_name}")
            return {
                "jsonrpc": jsonrpc,
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    elif method == "prompts/list":
        # Return empty list - docomatic-mcp-service doesn't expose prompts
        return {
            "jsonrpc": jsonrpc,
            "id": request_id,
            "result": {
                "prompts": []
            }
        }
    elif method == "resources/list":
        # Return empty list - docomatic-mcp-service doesn't expose resources
        return {
            "jsonrpc": jsonrpc,
            "id": request_id,
            "result": {
                "resources": []
            }
        }
    else:
        return {
            "jsonrpc": jsonrpc,
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


async def handle_sse_request(request: Dict[str, Any]) -> str:
    """Handle SSE request (returns JSON-RPC response as SSE format string)."""
    # Check if this is a JSON-RPC request
    if "jsonrpc" in request:
        result = await handle_jsonrpc_request(request)
        return f"data: {json.dumps(result)}\n\n"
    
    # For GET requests, return tools/list by default (for Cursor SSE discovery)
    method = request.get("method", "tools/list")
    if method == "tools/list" or method == "list_functions":
        # Return proper tools/list response for MCP SSE
        tool_schemas = get_tool_schemas()
        tools = []
        for tool_name, tool_def in tool_schemas.items():
            tools.append({
                "name": tool_def["name"],
                "description": tool_def["description"],
                "inputSchema": tool_def["inputSchema"]
            })
        response = {
            "jsonrpc": "2.0",
            "id": None,
            "result": {
                "tools": tools
            }
        }
        return f"data: {json.dumps(response)}\n\n"
    else:
        # Try as JSON-RPC request
        result = await handle_jsonrpc_request(request)
        return f"data: {json.dumps(result)}\n\n"


@app.post("/mcp/sse")
async def mcp_sse_post(request: dict = Body(...)):
    """Server-Sent Events endpoint for MCP (POST)."""
    result = await handle_jsonrpc_request(request)
    # Return as SSE format for Cursor's SSE client
    sse_result = f"data: {json.dumps(result)}\n\n"
    return StreamingResponse(content=sse_result, media_type="text/event-stream")


@app.get("/mcp/sse")
async def mcp_sse_get():
    """Server-Sent Events endpoint for MCP (GET).
    
    Returns discovery information (tools, prompts, resources) for Cursor SSE.
    Sends multiple SSE events: initialize, tools/list, prompts/list, resources/list.
    """
    async def generate_sse_stream():
        """Generate SSE stream with all discovery information.
        
        Keeps connection open for UI discovery. Sends discovery events
        and then keeps connection alive for bidirectional communication.
        """
        import asyncio
        
        # Send initialize response
        init_response = await handle_jsonrpc_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "cursor",
                    "version": "1.0.0"
                }
            }
        })
        yield f"data: {json.dumps(init_response)}\n\n"
        
        await asyncio.sleep(0.1)
        
        # Send tools/list
        tools_response = await handle_jsonrpc_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })
        tools_count = len(tools_response.get('result', {}).get('tools', []))
        logger.info(f"MCP SSE GET: Sending {tools_count} tools")
        yield f"data: {json.dumps(tools_response)}\n\n"
        
        await asyncio.sleep(0.1)
        
        # Send prompts/list
        prompts_response = await handle_jsonrpc_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "prompts/list",
            "params": {}
        })
        yield f"data: {json.dumps(prompts_response)}\n\n"
        
        await asyncio.sleep(0.1)
        
        # Send resources/list
        resources_response = await handle_jsonrpc_request({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/list",
            "params": {}
        })
        yield f"data: {json.dumps(resources_response)}\n\n"
        
        # Keep connection open for UI discovery
        # Send periodic keepalive to prevent connection timeout
        try:
            while True:
                await asyncio.sleep(30)  # Send keepalive every 30 seconds
                yield f": keepalive\n\n"
        except asyncio.CancelledError:
            logger.info("MCP SSE GET: Connection closed by client")
            raise
    
    return StreamingResponse(
        generate_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "doc-o-matic"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)

