from sqlalchemy.orm import Session

from app.database.models import Conversation, Message


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def update_message(
        self,
        message_id: str,
        content: str,
        sql: str | None = None,
    ) -> Message:
        message = (
            self.db.query(Message)
            .filter(Message.id == message_id)
            .first()
        )

        if not message:
            raise ValueError(
                f"Message not found: {message_id}"
            )

        message.content = content
        message.sql = sql

        self.db.commit()
        self.db.refresh(message)

        return message