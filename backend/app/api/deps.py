from __future__ import annotations

import uuid
from datetime import timedelta

import jwt
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token, hash_api_key
from app.core.time import utcnow
from app.db.session import get_db
from app.models.entities import ApiKey, User
from app.services.ratelimit import allow_request
from app.services.settings_store import get_settings_map

bearer = HTTPBearer(auto_error=False)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host
    return ""


def get_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> ApiKey:
    token = None
    if credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials.strip()
    if not token and x_api_key:
        token = x_api_key.strip()
    if not token or not token.startswith("sk_stt_"):
        raise AppError("unauthorized", "کلید API معتبر نیست.", 401)
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(token)))
    if api_key is None or api_key.status != "active":
        raise AppError("unauthorized", "کلید API معتبر نیست.", 401)
    if api_key.client is None or api_key.client.status != "active":
        raise AppError("forbidden", "کلاینت این کلید غیرفعال است.", 403)
    if api_key.last_used_at is None or utcnow() - api_key.last_used_at > timedelta(seconds=60):
        api_key.last_used_at = utcnow()
        db.commit()
    return api_key


def enforce_rate_limit(
    api_key: ApiKey = Depends(get_api_key),
    db: Session = Depends(get_db),
) -> ApiKey:
    settings_map = get_settings_map(db)
    limit = api_key.rate_limit_per_minute or int(settings_map["rate_limit_per_minute"])
    allow_request(api_key.id, int(limit))
    return api_key


def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("unauthorized", "ورود لازم است.", 401)
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise AppError("unauthorized", "نشست ورود نامعتبر است.", 401) from exc
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (TypeError, ValueError) as exc:
        raise AppError("unauthorized", "نشست ورود نامعتبر است.", 401) from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError("unauthorized", "کاربر ادمین پیدا نشد.", 401)
    return user
