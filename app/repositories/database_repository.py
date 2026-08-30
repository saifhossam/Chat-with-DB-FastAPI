"""Postgres-backed repository for database connections."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import DatabaseConnection


class DatabaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, database_id: str, owner_id: str) -> DatabaseConnection | None:
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.id == database_id,
            DatabaseConnection.owner_id == owner_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def save(self, database: DatabaseConnection) -> DatabaseConnection:
        self.db.add(database)
        self.db.commit()
        self.db.refresh(database)
        return database