from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.llm_factory import agent, llm
from app.ai.tools import execute_readonly, get_schema
from app.api.auth import current_user_id
from app.database.connection import get_db
from app.database.models import Conversation, Message
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.database_repository import DatabaseRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.database_service import DatabaseService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    database_service = DatabaseService(DatabaseRepository(db))
    return ChatService(database_service, ConversationRepository(db), agent)


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user_id: str = Depends(current_user_id),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    conversation, sql = chat_service.ask(user_id, payload.database_id, payload.message)
    return ChatResponse(
        conversation_id=conversation.id,
        answer=conversation.messages[-1].content,
        sql=sql,
    )


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    database_service = DatabaseService(DatabaseRepository(db))
    conversations = ConversationRepository(db)
    database = database_service.get_owned(payload.database_id, user_id)

    async def generate():
        full_answer = ""
        sql = None
        try:
            # كل chunk بنبعته بصيغة SSE: "data: النص\n\n"
            # الصيغة دي هي اللي بتخلي Postman (والمتصفحات) تعرض كل جزء اول ما يوصل
            yield "data: جاري قراءة هيكل قاعدة البيانات...\n\n"
            schema = get_schema(database.url)

            yield "data: جاري توليد كويري SQL...\n\n"
            sql = llm.generate_sql(payload.message, schema)
            yield f"data: SQL: {sql}\n\n"

            yield "data: جاري تنفيذ الكويري على قاعدة بياناتك...\n\n"
            rows = execute_readonly(database.url, sql)

            for chunk in llm.answer_stream(payload.message, schema, rows):
                if await request.is_disconnected():
                    break
                full_answer += chunk
                # لازم كل سطور جديدة جوه الـ chunk تتبدل بمسافة عشان صيغة SSE
                # مبتقبلش newline خام جوه سطر الـ data الواحد
                safe_chunk = chunk.replace("\n", " ")
                yield f"data: {safe_chunk}\n\n"

        except Exception as error:
            error_message = f"حصل خطأ اثناء توليد الرد: {error}"
            full_answer += f"\n[{error_message}]"
            yield f"data: {error_message}\n\n"

        finally:
            if full_answer.strip():
                conversation = Conversation(
                    id=str(uuid4()),
                    user_id=user_id,
                    database_id=payload.database_id,
                    messages=[
                        Message(id=str(uuid4()), role="user", content=payload.message),
                        Message(id=str(uuid4()), role="assistant", content=full_answer, sql=sql),
                    ],
                )
                conversations.save(conversation)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )