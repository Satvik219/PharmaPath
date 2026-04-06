from __future__ import annotations

from pharmapath.db.connection import get_connection


class UserRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

    def create_tenant(self, tenant_id: str, name: str, created_at: str) -> None:
        with get_connection(self.database_path) as connection:
            connection.execute(
                "INSERT INTO tenants (id, name, created_at) VALUES (?, ?, ?)",
                (tenant_id, name, created_at),
            )
            connection.commit()

    def create_user(
        self,
        user_id: str,
        email: str,
        password_hash: str,
        role: str,
        tenant_id: str,
        name: str,
        created_at: str,
    ) -> None:
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO users (id, email, password_hash, role, tenant_id, name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, email, password_hash, role, tenant_id, name, created_at),
            )
            connection.commit()

    def find_by_email(self, email: str):
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            return dict(row) if row else None

