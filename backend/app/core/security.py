from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from typing import Any, Dict, Optional

from backend.app.core.config import SECRET_KEY, TOKEN_EXPIRE_HOURS

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_PATTERN_RE = re.compile(r"(javascript:|onerror=|onload=|<script|</script>)", re.IGNORECASE)
_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "secret",
    "secret_key",
    "token",
    "access_token",
    "authorization",
    "ai_api_key",
    "api_key",
}


def sanitize_text(value: str, max_length: int = 1000) -> str:
    """Strip HTML tags and dangerous script patterns to prevent XSS."""
    if not isinstance(value, str):
        raise ValueError("Expected string input.")
    cleaned = _HTML_TAG_RE.sub("", value)
    cleaned = _SCRIPT_PATTERN_RE.sub("", cleaned)
    cleaned = cleaned.strip()
    if len(cleaned) > max_length:
        raise ValueError(f"Input exceeds maximum allowed length of {max_length} characters.")
    return cleaned


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a random 16-byte salt."""
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")
    salt = secrets.token_hex(16)
    iterations = 120_000
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${derived}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2-HMAC-SHA256 hash."""
    try:
        algorithm, iter_str, salt, expected_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return hmac.compare_digest(derived, expected_hex)
    except Exception:
        return False


def create_access_token(user_id: str, expires_in_seconds: Optional[int] = None) -> str:
    """Create a signed HMAC-SHA256 access token for session authentication."""
    ttl = expires_in_seconds if expires_in_seconds is not None else TOKEN_EXPIRE_HOURS * 3600
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl,
        "jti": secrets.token_hex(8),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_access_token(token: str) -> Optional[str]:
    """Verify a signed access token and return user_id if valid and unexpired."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, signature = token.split(".", 1)
        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        padding = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode((payload_b64 + padding).encode("ascii")).decode("utf-8")
        payload = json.loads(payload_json)
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        user_id = payload.get("sub")
        return str(user_id) if user_id else None
    except Exception:
        return None


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields and personal identifiers before logging (TC-36)."""
    sanitized: Dict[str, Any] = {}
    for key, value in data.items():
        lower_key = key.lower()
        if lower_key in _SENSITIVE_KEYS or "secret" in lower_key or "password" in lower_key or "token" in lower_key:
            sanitized[key] = "[REDACTED]"
        elif lower_key in {"display_name", "login_identifier", "email"}:
            sanitized[key] = "[REDACTED_PII]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    return sanitized
