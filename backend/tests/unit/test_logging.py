from app.core.logging import redact_sensitive_values


def test_structured_log_processor_redacts_sensitive_keys_and_pan_patterns() -> None:
    redacted = redact_sensitive_values(
        None,
        "info",
        {
            "event": "request_complete",
            "salary": "1250000",
            "nested": {"name": "Private User", "authorization": "opaque-token"},
            "note": "Example identifiers XXXXX0000X and xxxxx0000x must not appear.",
            "status_code": 200,
        },
    )

    assert redacted["salary"] == "[REDACTED]"
    assert redacted["nested"] == {
        "name": "[REDACTED]",
        "authorization": "[REDACTED]",
    }
    assert "[REDACTED]" in redacted["note"]
    assert "XXXXX0000X" not in redacted["note"]
    assert "xxxxx0000x" not in redacted["note"]
    assert redacted["status_code"] == 200
