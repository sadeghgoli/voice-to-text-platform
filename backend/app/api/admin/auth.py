from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_current_admin
from app.core.errors import AppError
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.entities import User
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["Admin Auth"])


class LoginBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


def _user_payload(user: User) -> dict:
    return {"id": str(user.id), "email": user.email, "full_name": user.full_name, "role": user.role}


@router.post("/login", summary="Admin login")
def login(body: LoginBody, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(user.password_hash, body.password):
        raise AppError("unauthorized", "ایمیل یا رمز عبور نادرست است.", 401)
    write_audit(
        db,
        actor_type="admin",
        actor_id=str(user.id),
        action="auth.login",
        resource_type="user",
        resource_id=str(user.id),
        ip=client_ip(request),
    )
    db.commit()
    return {"access_token": create_access_token(str(user.id), user.role), "token_type": "bearer", "user": _user_payload(user)}


@router.get("/me", summary="Current admin")
def me(user: User = Depends(get_current_admin)):
    return _user_payload(user)
