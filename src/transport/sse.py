import json


def sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event string."""
    payload = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


def mcp_response(request_id, result: dict) -> dict:
    """Wrap a tool result in MCP JSON-RPC 2.0 response format."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2, default=str)
                }
            ]
        }
    }


def mcp_error(request_id, code: int, message: str) -> dict:
    """Wrap an error in MCP JSON-RPC 2.0 error format."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }
