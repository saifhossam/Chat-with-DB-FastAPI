"""API schemas for connections managed by a user."""
from pydantic import BaseModel, Field


class DatabaseCreate(BaseModel):
    name: str = Field(min_length=1)
    url: str = Field(description="Example: sqlite:///./sample.db")


class DatabaseResponse(DatabaseCreate):
    id: str
    owner_id: str
