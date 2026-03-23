import json
import time
import boto3

_cache: dict = {}
_secrets_client = boto3.client("secretsmanager")
TTL_SECONDS = 300  # 5 minutes


def get_secret(secret_name: str) -> dict:
    """Fetch secret from Secrets Manager with local TTL cache."""
    cached = _cache.get(secret_name)
    if cached and time.time() - cached["ts"] < TTL_SECONDS:
        return cached["value"]

    response = _secrets_client.get_secret_value(SecretId=secret_name)
    secret_string = response.get("SecretString", "{}")
    value = json.loads(secret_string)

    _cache[secret_name] = {"value": value, "ts": time.time()}
    return value
