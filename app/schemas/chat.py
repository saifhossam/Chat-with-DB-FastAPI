from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    database_id: str
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sql: str | None = None
