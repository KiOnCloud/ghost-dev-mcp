import os
import hmac
from src.utils.secrets import get_secret

SECRET_NAME = os.environ.get("API_KEY_SECRET_NAME", "prod/ghost-developer/api-key")


def lambda_handler(event: dict, context) -> bool:
    """
    Lambda Authorizer for API Gateway HTTP API (simple response format).
    Validates the x-api-key header against the value stored in Secrets Manager.
    Returns True (allow) or False (deny).
    """
    provided_key = (event.get("headers") or {}).get("x-api-key", "")

    if not provided_key:
        return {"isAuthorized": False}

    try:
        secret = get_secret(SECRET_NAME)
        expected_key = secret.get("api_key", "")
    except Exception:
        return {"isAuthorized": False}

    # Constant-time comparison to prevent timing attacks
    authorized = hmac.compare_digest(provided_key.encode(), expected_key.encode())
    return {"isAuthorized": authorized}
