from .list_dlqs import list_dlqs
from .inspect_dlq import inspect_dlq_payload
from .search_log_groups import search_log_groups
from .get_error_traces import get_error_traces

TOOL_REGISTRY = {
    "list_dlqs": {
        "fn": list_dlqs,
        "description": "List all SQS Dead Letter Queues in the account, with message depth. Use this first to discover which DLQ to inspect.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Optional extra keyword to narrow results (e.g. 'payment', 'order')"
                }
            }
        }
    },
    "inspect_dlq_payload": {
        "fn": inspect_dlq_payload,
        "description": "Peek at failed messages in a specific SQS Dead Letter Queue without deleting them.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "queue_url": {
                    "type": "string",
                    "description": "Full SQS DLQ URL (get this from list_dlqs)"
                },
                "max_messages": {
                    "type": "integer",
                    "description": "Number of messages to retrieve (1–10, default 5)",
                    "default": 5
                }
            },
            "required": ["queue_url"]
        }
    },
    "search_log_groups": {
        "fn": search_log_groups,
        "description": "Search CloudWatch Log Groups by keyword. Use this to discover which log groups exist before calling get_error_traces.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Keyword to match against log group names (e.g. 'payment', 'api', 'lambda')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results to return (default 20)",
                    "default": 20
                }
            },
            "required": ["keyword"]
        }
    },
    "get_error_traces": {
        "fn": get_error_traces,
        "description": "Query one or more CloudWatch Log Groups for errors using Logs Insights. Supports async polling for large queries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "log_groups": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of log group names to query (get from search_log_groups)"
                },
                "log_group": {
                    "type": "string",
                    "description": "Single log group name (convenience alias)"
                },
                "minutes_ago": {
                    "type": "integer",
                    "description": "How many minutes back to search (default 30)",
                    "default": 30
                },
                "filter_pattern": {
                    "type": "string",
                    "description": "Regex pattern to filter log lines (default: ERROR|Exception|5xx)",
                    "default": "ERROR|Exception|5[0-9][0-9]"
                },
                "query_id": {
                    "type": "string",
                    "description": "Poll an existing async query by ID. If provided, all other params are ignored."
                }
            }
        }
    }
}
