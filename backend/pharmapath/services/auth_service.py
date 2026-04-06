from __future__ import annotations

from flask import current_app

from pharmapath.core.security import generate_token, hash_password, verify_password
from pharmapath.repositories.user_repository import UserRepository
from pharmapath.utils.ids import new_id
from pharmapath.utils.time import utc_now_iso


class AuthService:
    def __init__(self) -> None:
        self.repo = UserRepository(current_app.config["DATABASE_PATH"])

    def register(self, payload: dict) -> dict:
        existing = self.repo.find_by_email(payload["email"])
        if existing:
            raise ValueError("Email already exists")

        tenant_id = new_id()
        user_id = new_id()
        now = utc_now_iso()

        self.repo.create_tenant(tenant_id, f"{payload['name']}'s tenant", now)
        self.repo.create_user(
            user_id=user_id,
            email=payload["email"],
            password_hash=hash_password(payload["password"]),
            role=payload["role"],
            tenant_id=tenant_id,
            name=payload["name"],
            created_at=now,
        )

        return {
            "user_id": user_id,
            "jwt_token": generate_token(
                {"sub": user_id, "email": payload["email"], "tenant_id": tenant_id, "role": payload["role"]},
                current_app.config["SECRET_KEY"],
            ),
            "refresh_token": generate_token({"sub": user_id, "kind": "refresh"}, current_app.config["SECRET_KEY"], 86400),
        }

    def login(self, payload: dict) -> dict:
        user = self.repo.find_by_email(payload["email"])
        if not user or not verify_password(payload["password"], user["password_hash"]):
            raise ValueError("Invalid credentials")

        return {
            "jwt_token": generate_token(
                {"sub": user["id"], "email": user["email"], "tenant_id": user["tenant_id"], "role": user["role"]},
                current_app.config["SECRET_KEY"],
            ),
            "refresh_token": generate_token({"sub": user["id"], "kind": "refresh"}, current_app.config["SECRET_KEY"], 86400),
            "expires_in": 3600,
        }

    def refresh(self, refresh_token: str) -> dict:
        return {
            "jwt_token": generate_token({"kind": "access"}, current_app.config["SECRET_KEY"]),
            "expires_in": 3600,
        }

