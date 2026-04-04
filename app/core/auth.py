from __future__ import annotations

import base64
import hashlib
import hmac
import json

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import get_settings
from app.schemas.ask import AllowedRole


bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    api_key: str
    role: AllowedRole
    subject: str | None = None


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def create_demo_token(role: AllowedRole, subject: str = "demo-user") -> str:
    settings = get_settings()
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    payload = {"sub": subject, "role": role}

    header_b64 = _b64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    payload_b64 = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token format.",
        ) from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    provided_signature = _b64url_decode(signature_b64)

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token signature.",
        )

    try:
        return json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token payload.",
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    payload = decode_token(credentials.credentials)
    role = payload.get("role")
    if role not in {"operations_analyst", "regional_manager", "exec_viewer"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token role is not allowed.",
        )

    return AuthenticatedUser(
        api_key=credentials.credentials,
        role=role,
        subject=payload.get("sub"),
    )
