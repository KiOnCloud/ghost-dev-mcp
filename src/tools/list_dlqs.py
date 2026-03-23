import boto3

sqs_client = boto3.client("sqs")


def list_dlqs(keyword: str = "") -> dict:
    """
    List all SQS queues that look like Dead Letter Queues.
    Matches queues containing 'dlq' or 'dead' in the name (case-insensitive),
    optionally filtered further by an additional keyword.
    """
    results = []

    for prefix in ["", keyword] if keyword else [""]:
        paginator = sqs_client.get_paginator("list_queues") if hasattr(sqs_client, "get_paginator") else None

        response = sqs_client.list_queues(
            QueueNamePrefix=prefix,
            MaxResults=100
        )
        urls = response.get("QueueUrls", [])

        # Handle pagination manually (list_queues returns NextToken)
        while True:
            next_token = response.get("NextToken")
            if not next_token:
                break
            response = sqs_client.list_queues(
                QueueNamePrefix=prefix,
                NextToken=next_token,
                MaxResults=100
            )
            urls.extend(response.get("QueueUrls", []))

        for url in urls:
            queue_name = url.split("/")[-1].lower()
            if "dlq" in queue_name or "dead" in queue_name or (keyword and keyword.lower() in queue_name):
                results.append(url)

    # Deduplicate
    unique_urls = list(dict.fromkeys(results))

    # Batch fetch approximate depths
    queues = []
    for url in unique_urls:
        try:
            attrs = sqs_client.get_queue_attributes(
                QueueUrl=url,
                AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"]
            )["Attributes"]
            depth = int(attrs.get("ApproximateNumberOfMessages", 0))
            not_visible = int(attrs.get("ApproximateNumberOfMessagesNotVisible", 0))
        except Exception:
            depth, not_visible = -1, -1

        queues.append({
            "queue_name": url.split("/")[-1],
            "queue_url": url,
            "messages_available": depth,
            "messages_in_flight": not_visible
        })

    queues.sort(key=lambda q: q["messages_available"], reverse=True)

    return {
        "total_dlqs_found": len(queues),
        "hint": "Use inspect_dlq_payload(queue_url=...) to peek at messages in a specific queue.",
        "queues": queues
    }
