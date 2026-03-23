import json
import boto3
from src.utils.redact import redact_sensitive

sqs_client = boto3.client("sqs")


def inspect_dlq_payload(queue_url: str, max_messages: int = 5) -> dict:
    """
    Peek at messages in a Dead Letter Queue without deleting them.
    VisibilityTimeout=30s keeps messages hidden briefly while we read,
    then they automatically return to the queue.
    """
    max_messages = max(1, min(max_messages, 10))

    # Get queue depth before receiving
    attrs = sqs_client.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"]
    )
    total_depth = int(attrs["Attributes"].get("ApproximateNumberOfMessages", 0))

    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=max_messages,
        VisibilityTimeout=30,
        AttributeNames=["All"],
        MessageAttributeNames=["All"]
    )

    raw_messages = response.get("Messages", [])
    parsed = []

    for msg in raw_messages:
        body = msg.get("Body", "")
        try:
            body_parsed = json.loads(body)
        except json.JSONDecodeError:
            body_parsed = body

        parsed.append({
            "message_id": msg["MessageId"],
            "sent_at": msg["Attributes"].get("SentTimestamp"),
            "receive_count": msg["Attributes"].get("ApproximateReceiveCount"),
            "body": redact_sensitive(body_parsed),
            "message_attributes": msg.get("MessageAttributes", {})
        })
        # NOTE: No DeleteMessage call — messages auto-return after VisibilityTimeout

    return {
        "queue_url": queue_url,
        "approximate_total_in_dlq": total_depth,
        "retrieved": len(parsed),
        "warning": "DLQ does not guarantee message order.",
        "note": "Messages are NOT deleted. They will return to the queue after 30s.",
        "messages": parsed
    }
