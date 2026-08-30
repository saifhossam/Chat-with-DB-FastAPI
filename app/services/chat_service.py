"""Orchestrates schema inspection, SQL generation, validation, and answering."""
from uuid import uuid4

from app.ai.agent import DatabaseAgent
from app.database.models import Conversation, Message
from app.repositories.conversation_repository import ConversationRepository
from app.services.database_service import DatabaseService


class ChatService:
    def __init__(self, databases: DatabaseService, conversations: ConversationRepository, agent: DatabaseAgent):
        self.databases = databases
        self.conversations = conversations
        self.agent = agent

    def ask(self, user_id: str, database_id: str, message: str) -> tuple[Conversation, str | None]:
        database = self.databases.get_owned(database_id, user_id)
        answer, sql = self.agent.ask(database.url, message)

        conversation = Conversation(
            id=str(uuid4()),
            user_id=user_id,
            database_id=database_id,
            messages=[
                Message(id=str(uuid4()), role="user", content=message),
                Message(id=str(uuid4()), role="assistant", content=answer, sql=sql),
            ],
        )
        return self.conversations.save(conversation), sql