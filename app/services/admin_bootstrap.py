import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password


def bootstrap_admin() -> None:
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    if not email and not password:
        return
    if not email or not password or len(password) < 8:
        raise RuntimeError(
            "Set both ADMIN_EMAIL and an ADMIN_PASSWORD of at least 8 characters"
        )

    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == email))
        if admin is None:
            admin = User(
                name=os.getenv("ADMIN_NAME", "Administrator"),
                email=email,
                password_hash=hash_password(password),
                role="admin",
            )
            db.add(admin)
        elif admin.role != "admin":
            admin.role = "admin"
        db.commit()