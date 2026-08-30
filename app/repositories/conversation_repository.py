"""Postgres-backed repository for conversations and their messages."""
from sqlalchemy.orm import Session

from app.database.models import Conversation


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, conversation: Conversation) -> Conversation:
        # الرسايل (Message objects) بتتحفظ تلقائي مع الـ conversation بسبب الـ relationship
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation