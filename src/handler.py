import json
import traceback
from src.tools import TOOL_REGISTRY
from src.transport.sse import mcp_response, mcp_error

MCP_VERSION = "2025-11-25"


def lambda_handler(event: dict, context) -> dict:
    path = event.get("rawPath", event.get("path", "/"))
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    headers = event.get("headers") or {}

    print(json.dumps({
        "method": method,
        "path": path,
        "accept": headers.get("accept", ""),
        "content_type": headers.get("content-type", ""),
        "body_preview": (event.get("body") or "")[:200],
    }))

    if path == "/health":
        return _ok({"status": "ok"})

    if path == "/mcp":
        if method == "GET":
            # Streamable HTTP (2025-03-26) — server push not supported
            return {
                "statusCode": 405,
                "headers": {"Content-Type": "application/json", "Allow": "POST"},
                "body": '{"error": "Method Not Allowed. Use POST for MCP Streamable HTTP."}'
            }
        if method == "POST":
            return _handle_tool_call(event)

    return _ok({"error": "Not found"}, status=404)


def _handle_initialize(request_id=0) -> dict:
    """Return MCP server capabilities and tool manifest."""
    tools = []
    for name, meta in TOOL_REGISTRY.items():
        tools.append({
            "name": name,
            "description": meta["description"],
            "inputSchema": meta["inputSchema"]
        })

    body = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": MCP_VERSION,
            "serverInfo": {"name": "aws-ghost-developer", "version": "1.0.0"},
            "capabilities": {"tools": {}},
            "tools": tools
        }
    }
    return _ok(body)


def _handle_tool_call(event: dict) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _ok(mcp_error(None, -32700, "Parse error"), status=400)

    request_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    if method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if tool_name not in TOOL_REGISTRY:
            return _ok(mcp_error(request_id, -32601, f"Unknown tool: {tool_name}"), status=404)

        try:
            result = TOOL_REGISTRY[tool_name]["fn"](**tool_args)
            return _ok(mcp_response(request_id, result))
        except TypeError as e:
            return _ok(mcp_error(request_id, -32602, f"Invalid params: {e}"), status=422)
        except Exception as e:
            traceback.print_exc()
            return _ok(mcp_error(request_id, -32603, f"Internal error: {str(e)}"), status=500)

    if method == "tools/list":
        return _handle_initialize(request_id)

    if method == "initialize":
        return _handle_initialize(request_id)

    if method and method.startswith("notifications/"):
        return {"statusCode": 202, "headers": {}, "body": ""}

    return _ok(mcp_error(request_id, -32601, f"Method not found: {method}"), status=404)


def _ok(body: dict, status: int = 200) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str)
    }
