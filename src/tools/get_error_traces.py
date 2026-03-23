import time
from datetime import datetime, timedelta, timezone
import boto3

logs_client = boto3.client("logs")

QUERY_TEMPLATE = """
fields @timestamp, @message, @logStream, @requestId
| filter @message like /{filter_pattern}/
| sort @timestamp desc
| limit 20
"""


def get_error_traces(
    log_groups: list = None,
    log_group: str = None,
    minutes_ago: int = 30,
    filter_pattern: str = "ERROR|Exception|5[0-9][0-9]",
    query_id: str = None
) -> dict:
    """
    Query one or more CloudWatch Log Groups for errors via Logs Insights.

    Flow:
      1. First call: starts query across all provided log groups,
         returns {status: RUNNING, query_id} if not yet complete.
      2. Poll call: pass query_id to retrieve results.

    Args:
        log_groups: List of log group names to query simultaneously.
        log_group:  Single log group (convenience alias, merged with log_groups).
        minutes_ago: Time window to search.
        filter_pattern: Regex pattern to match error lines.
        query_id: Poll an existing async query.
    """
    if query_id:
        return _poll_query(query_id)

    # Merge single + list inputs
    targets = list(log_groups or [])
    if log_group and log_group not in targets:
        targets.append(log_group)

    if not targets:
        return {
            "error": "Provide at least one log group via log_groups=[...] or log_group='...'.",
            "hint": "Use search_log_groups(keyword='...') to discover available log groups."
        }

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=minutes_ago)
    query_string = QUERY_TEMPLATE.format(filter_pattern=filter_pattern).strip()

    response = logs_client.start_query(
        logGroupNames=targets,          # multi-group support
        startTime=int(start_time.timestamp()),
        endTime=int(end_time.timestamp()),
        queryString=query_string
    )
    started_id = response["queryId"]

    # Try to resolve synchronously within 3s (fast for small log groups)
    for _ in range(3):
        time.sleep(1)
        result = _poll_query(started_id)
        if result["status"] == "Complete":
            result["log_groups_queried"] = targets
            result["time_range_minutes"] = minutes_ago
            return result

    return {
        "status": "RUNNING",
        "query_id": started_id,
        "log_groups_queried": targets,
        "time_range_minutes": minutes_ago,
        "message": "Query still running. Call get_error_traces(query_id='...') to poll."
    }


def _poll_query(query_id: str) -> dict:
    response = logs_client.get_query_results(queryId=query_id)
    status = response["status"]

    if status != "Complete":
        return {
            "status": status,
            "query_id": query_id,
            "message": "Not yet complete. Poll again shortly."
        }

    results = [
        {field["field"]: field["value"] for field in row}
        for row in response.get("results", [])
    ]

    return {
        "status": "Complete",
        "query_id": query_id,
        "total_results": len(results),
        "statistics": response.get("statistics", {}),
        "results": results
    }
