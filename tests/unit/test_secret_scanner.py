from src.compliance.secret_scanner import scan_and_redact_secrets


def test_scan_aws_key():
    code = "aws_access_key_id = 'AKIAIOSFODNN7EXAMPLE'"
    redacted, has_secrets, types = scan_and_redact_secrets(code)
    
    assert has_secrets is True
    assert "[REDACTED_AWS_KEY_ID]" in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted


def test_scan_private_key():
    code = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
    redacted, has_secrets, types = scan_and_redact_secrets(code)
    
    assert has_secrets is True
    assert "[REDACTED_PRIVATE_KEY]" in redacted


def test_scan_clean_code():
    code = "def add(a, b):\n    return a + b"
    redacted, has_secrets, types = scan_and_redact_secrets(code)
    
    assert has_secrets is False
    assert redacted == code
