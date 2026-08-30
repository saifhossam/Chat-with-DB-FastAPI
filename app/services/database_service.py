"""Use cases for registering and retrieving database connections."""
from uuid import uuid4

from app.core.exceptions import DatabaseNotFoundError
from app.database.models import DatabaseConnection
from app.repositories.database_repository import DatabaseRepository


class DatabaseService:
    def __init__(self, databases: DatabaseRepository):
        self.databases = databases

    def add(self, owner_id: str, name: str, url: str) -> DatabaseConnection:
        database = DatabaseConnection(id=str(uuid4()), owner_id=owner_id, name=name, url=url)
        return self.databases.save(database)

    def get_owned(self, database_id: str, owner_id: str) -> DatabaseConnection:
        database = self.databases.get(database_id, owner_id)
        if not database:
            raise DatabaseNotFoundError("Database connection was not found")
        return database

    ss