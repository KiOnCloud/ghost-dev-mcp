from datetime import datetime, timezone
import boto3

logs_client = boto3.client("logs")


def search_log_groups(keyword: str, limit: int = 20) -> dict:
    """
    Discover CloudWatch Log Groups whose name contains the given keyword.
    Returns groups sorted by most recently active, with size info.
    Useful before calling get_error_traces to know which log_groups to query.
    """
    keyword_lower = keyword.lower()
    matches = []

    paginator = logs_client.get_paginator("describe_log_groups")
    for page in paginator.paginate(PaginationConfig={"MaxItems": 500}):
        for group in page.get("logGroups", []):
            name = group.get("logGroupName", "")
            if keyword_lower in name.lower():
                last_event_ms = group.get("creationTime", 0)
                stored_bytes = group.get("storedBytes", 0)

                matches.append({
                    "log_group_name": name,
                    "stored_mb": round(stored_bytes / 1_048_576, 2),
                    "retention_days": group.get("retentionInDays", "never expires"),
                    "created_at": _ms_to_iso(group.get("creationTime"))
                })

    # Sort: /aws/lambda/ groups first, then alphabetical
    matches.sort(key=lambda g: (
        0 if "/aws/lambda/" in g["log_group_name"] else 1,
        g["log_group_name"]
    ))
    matches = matches[:limit]

    return {
        "keyword": keyword,
        "total_found": len(matches),
        "hint": "Pass one or more log_group_name values to get_error_traces(log_groups=[...]).",
        "log_groups": matches
    }


def _ms_to_iso(ms: int) -> str:
    if not ms:
        return "unknown"
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
