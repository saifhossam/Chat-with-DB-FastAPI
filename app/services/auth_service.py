"""Application use cases for registration and login."""
from uuid import uuid4

from app.core.exceptions import InvalidCredentialsError
from app.core.security import create_access_token, hash_password, verify_password
from app.database.models import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, users: UserRepository):
        self.users = users

    def register(self, email: str, password: str) -> str:
        user = User(id=str(uuid4()), email=email, password_hash=hash_password(password))
        self.users.save(user)
        return create_access_token(user.id)

    def login(self, email: str, password: str) -> str:
        user = self.users.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        return create_access_token(user.id)