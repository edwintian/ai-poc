import hmac


def check_password(supplied: str, expected: str) -> bool:
    """Constant-time comparison; an unset (empty) expected password never matches."""
    if not expected:
        return False
    return hmac.compare_digest(supplied.encode(), expected.encode())
