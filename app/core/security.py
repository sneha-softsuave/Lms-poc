"""JWT (hand-rolled HS256) + bcrypt password hashing.

Ported from ThinkArguments' app/core/security.py, trimmed to the tokens this POC
needs (access + refresh). Kept dependency-light: standard-library HMAC/JWT so
there is no python-jose/PyJWT version drift.
"""

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(encoded: str) -> bytes:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode((encoded + padding).encode("ascii"))


def _hs_sign(signing_input: bytes, secret: str, algorithm: str) -> bytes:
    digestmod = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}.get(
        algorithm
    )
    if digestmod is None:
        raise ValueError(f"Unsupported JWT algorithm: {algorithm}")
    return hmac.new(secret.encode("utf-8"), signing_input, digestmod=digestmod).digest()


def _jwt_encode(payload: dict[str, Any], secret: str, algorithm: str) -> str:
    header = {"alg": algorithm, "typ": "JWT"}

    def _default(value: Any):
        if isinstance(value, datetime):
            return int(value.timestamp())
        raise TypeError(f"{type(value).__name__} is not JSON serializable")

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
    payload_b64 = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True, default=_default).encode()
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig_b64 = _b64url_encode(_hs_sign(signing_input, secret, algorithm))
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _jwt_decode(token: str, secret: str, algorithms: list[str]) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    header = json.loads(_b64url_decode(parts[0]))
    alg = header.get("alg")
    if alg not in algorithms:
        raise ValueError("JWT algorithm not allowed")
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    if not hmac.compare_digest(_b64url_decode(parts[2]), _hs_sign(signing_input, secret, alg)):
        raise ValueError("JWT signature mismatch")
    payload: dict[str, Any] = json.loads(_b64url_decode(parts[1]))
    exp = payload.get("exp")
    if exp is not None and time.time() > float(exp):
        raise ValueError("JWT expired")
    return payload


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(UTC), "jti": secrets.token_urlsafe(16)})
    return _jwt_encode(to_encode, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(UTC),
            "jti": secrets.token_urlsafe(16),
            "token_type": "refresh",
        }
    )
    return _jwt_encode(to_encode, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict[str, Any] | None:
    try:
        return _jwt_decode(token, settings.JWT_SECRET_KEY, [settings.JWT_ALGORITHM])
    except Exception as exc:  # noqa: BLE001
        logger.warning("JWT verification failed (%s): token rejected", type(exc).__name__)
        return None


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    payload = verify_token(token)
    if payload and payload.get("token_type") == "refresh":
        return payload
    return None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
