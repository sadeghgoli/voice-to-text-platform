from __future__ import annotations

import argparse

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.entities import User


def create_admin(email: str, password: str, full_name: str) -> str:
    normalized = email.strip().lower()
    if len(password) < 8:
        raise SystemExit("رمز عبور ادمین باید حداقل ۸ کاراکتر باشد.")
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == normalized))
        if existing is not None:
            return "exists"
        db.add(
            User(
                email=normalized,
                password_hash=hash_password(password),
                full_name=full_name.strip() or "مدیر سیستم",
                role="admin",
                is_active=True,
            )
        )
        db.commit()
        return "created"
    finally:
        db.close()


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Create the first admin user")
    parser.add_argument("--email", default=settings.admin_email)
    parser.add_argument("--password", default=settings.admin_password)
    parser.add_argument("--name", default=settings.admin_name)
    args = parser.parse_args()
    if not args.email or not args.password:
        print("ADMIN_EMAIL یا ADMIN_PASSWORD تنظیم نشده؛ ساخت ادمین رد شد.")
        return
    result = create_admin(args.email, args.password, args.name)
    if result == "exists":
        print(f"ادمین از قبل وجود دارد: {args.email}")
    else:
        print(f"ادمین ساخته شد: {args.email}")


if __name__ == "__main__":
    main()
