from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings
from app.core.time import utcnow

_hasher = PasswordHasher()
API_KEY_PREFIX = "sk_stt_"


def generate_api_key() -> tuple[str, str, str]:
    raw = API_KEY_PREFIX + secrets.token_urlsafe(32)
    return raw, hash_api_key(raw), raw[:16]


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def mask_api_key(prefix: str) -> str:
    return f"{prefix}************"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: str, role: str) -> str:
    settings = get_settings()
    expire = utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
