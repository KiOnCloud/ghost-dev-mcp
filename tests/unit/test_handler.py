import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import patch, MagicMock
from src.handler import lambda_handler


def _post_event(body: dict) -> dict:
    return {
        "rawPath": "/mcp",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps(body)
    }


def test_health():
    event = {"rawPath": "/health", "requestContext": {"http": {"method": "GET"}}}
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"])["status"] == "ok"


def test_unknown_tool():
    event = _post_event({
        "jsonrpc": "2.0", "id": 1,
        "method": "tools/call",
        "params": {"name": "does_not_exist", "arguments": {}}
    })
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert "error" in body


def test_tools_list():
    event = {"rawPath": "/mcp", "requestContext": {"http": {"method": "GET"}}}
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    tool_names = [t["name"] for t in body["result"]["tools"]]
    assert "list_dlqs" in tool_names
    assert "inspect_dlq_payload" in tool_names
    assert "search_log_groups" in tool_names
    assert "get_error_traces" in tool_names


def test_inspect_dlq_bad_params():
    event = _post_event({
        "jsonrpc": "2.0", "id": 2,
        "method": "tools/call",
        "params": {"name": "inspect_dlq_payload", "arguments": {}}  # missing queue_url
    })
    with patch("src.tools.inspect_dlq.sqs_client") as mock_sqs:
        mock_sqs.get_queue_attributes.side_effect = TypeError("missing queue_url")
        resp = lambda_handler(event, None)
    assert resp["statusCode"] in (422, 500)
