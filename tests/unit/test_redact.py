import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.utils.redact import redact_sensitive


def test_redacts_dict_keys():
    data = {"username": "alice", "password": "s3cr3t", "amount": 100}
    result = redact_sensitive(data)
    assert result["password"] == "[REDACTED]"
    assert result["username"] == "alice"
    assert result["amount"] == 100


def test_redacts_nested():
    data = {"db": {"host": "localhost", "secret": "abc123"}}
    result = redact_sensitive(data)
    assert result["db"]["secret"] == "[REDACTED]"
    assert result["db"]["host"] == "localhost"


def test_redacts_list():
    data = [{"token": "xyz"}, {"name": "ok"}]
    result = redact_sensitive(data)
    assert result[0]["token"] == "[REDACTED]"
    assert result[1]["name"] == "ok"


def test_passthrough_non_sensitive():
    data = {"service": "payments", "error_count": 5}
    result = redact_sensitive(data)
    assert result == data
