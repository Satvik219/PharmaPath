from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def generate_token(payload: dict[str, Any], secret: str, expires_in: int = 3600) -> str:
    body = {**payload, "exp": int(time.time()) + expires_in}
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    return (
        base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")
        + "."
        + base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    )


def decode_token(token: str, secret: str) -> dict[str, Any] | None:
    try:
        payload_part, signature_part = token.split(".", 1)
        raw = base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4))
        signature = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
    except Exception:
        return None

    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        return None

    payload = json.loads(raw.decode("utf-8"))
    if payload.get("exp", 0) < time.time():
        return None
    return payload

