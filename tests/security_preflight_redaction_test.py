"""Production preflight output must not echo sensitive values."""
from core import preflight


def test_sensitive_messages_are_redacted():
    assert preflight.redact_preflight_message(
        "EINVITE_FIELD_ENCRYPTION_KEY is invalid"
    ) == "[redacted: sensitive configuration value]"
    assert preflight.redact_preflight_message(
        "the password is too short"
    ) == "[redacted: sensitive configuration value]"


def test_non_sensitive_diagnostics_remain_actionable():
    message = "Database file is missing"
    assert preflight.redact_preflight_message(message) == message
