import re

SENSITIVE_KEYS = {
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "authorization", "auth", "credential", "private_key", "access_key",
    "secret_key", "session_token"
}

SENSITIVE_PATTERN = re.compile(
    r"(password|secret|token|api_key|apikey|authorization|credential)[\"']?\s*[:=]\s*[\"']?[\w\-\.]+",
    re.IGNORECASE
)


def redact_sensitive(data, _depth=0):
    """Recursively redact sensitive values before returning to LLM."""
    if _depth > 10:
        return data

    if isinstance(data, dict):
        return {
            k: "[REDACTED]" if k.lower() in SENSITIVE_KEYS else redact_sensitive(v, _depth + 1)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [redact_sensitive(item, _depth + 1) for item in data]
    elif isinstance(data, str):
        return SENSITIVE_PATTERN.sub(lambda m: m.group(0).split("=")[0] + "=[REDACTED]", data)

    return data
