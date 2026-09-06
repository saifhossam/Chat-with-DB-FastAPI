import time
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.llm_factory import agent, llm
from app.ai.stream_throttler import stream_throttler
from app.ai.tools import execute_readonly, get_schema
from app.api.auth import current_user_id
from app.database.connection import get_db
from app.database.models import Conversation, Message
from app.middleware.rate_limiter import rate_limiter
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.database_repository import DatabaseRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.security.input_guardrail import input_guardrail
from app.security.output_guardrail import output_guardrail
from app.services.chat_service import ChatService
from app.services.database_service import DatabaseService

router = APIRouter(prefix="/chat", tags=["chat"])

# Save the streamed response every:

CHECKPOINT_SECONDS = 2.0
CHECKPOINT_EVERY_CHUNKS = 10


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    database_service = DatabaseService(DatabaseRepository(db))
    return ChatService(database_service, ConversationRepository(db), agent)


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user_id: str = Depends(current_user_id),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    # Security: Rate limiting
    rate_limiter.check_limit(user_id)
    
    # Security: Input guardrail
    input_guardrail.validate_or_raise(payload.message)
    
    conversation, sql = chat_service.ask(
        user_id,
        payload.database_id,
        payload.message,
    )

    # Security: Output guardrail
    output_guardrail.validate_or_raise(conversation.messages[-1].content)

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
    # Security: Rate limiting
    rate_limiter.check_limit(user_id)
    
    # Security: Input guardrail
    try:
        input_guardrail.validate_or_raise(payload.message)
    except Exception as e:
        # Record blocked attempt for abuse tracking
        rate_limiter.record_blocked_attempt(user_id, "input_guardrail_blocked")
        raise
    
    database_service = DatabaseService(DatabaseRepository(db))
    conversations = ConversationRepository(db)

    database = database_service.get_owned(
        payload.database_id,
        user_id,
    )

    # Create the conversation before starting the LLM stream.
    conversation = Conversation(
        id=str(uuid4()),
        user_id=user_id,
        database_id=payload.database_id,
        messages=[
            Message(
                id=str(uuid4()),
                role="user",
                content=payload.message,
            ),
            Message(
                id=str(uuid4()),
                role="assistant",
                content="",
                sql=None,
            ),
        ],
    )

    conversations.save(conversation)

    assistant_message = conversation.messages[-1]

    async def generate():
        full_answer = ""
        sql = None
        chunk_count = 0

        # Time of the last DB checkpoint.
        last_checkpoint = time.monotonic()

        try:
            yield "data: جاري قراءة هيكل قاعدة البيانات...\n\n"

            schema = get_schema(database.url)

            yield "data: جاري توليد كويري SQL...\n\n"

            sql = llm.generate_sql(
                payload.message,
                schema,
            )

            # Save SQL immediately because it is already available.
            assistant_message.sql = sql

            conversations.update_message(
                assistant_message.id,
                content=full_answer,
                sql=sql,
            )

            yield f"data: SQL: {sql}\n\n"

            yield "data: جاري تنفيذ الكويري على قاعدة بياناتك...\n\n"

            rows = execute_readonly(
                database.url,
                sql,
            )

            for chunk in llm.answer_stream(
                payload.message,
                schema,
                rows,
            ):
                if await request.is_disconnected():
                    break

                full_answer += chunk
                chunk_count += 1

                # Send the chunk immediately to the client.
                safe_chunk = chunk.replace("\n", " ")
                yield f"data: {safe_chunk}\n\n"

                # Security: Stream throttling
                await stream_throttler.throttle()

                # Check whether we should checkpoint the DB.
                now = time.monotonic()

                should_checkpoint = (
                    chunk_count % CHECKPOINT_EVERY_CHUNKS == 0
                    or now - last_checkpoint >= CHECKPOINT_SECONDS
                )

                if should_checkpoint:
                    conversations.update_message(
                        assistant_message.id,
                        content=full_answer,
                        sql=sql,
                    )

                    last_checkpoint = now

                    print(
                        f"DB CHECKPOINT: "
                        f"chunks={chunk_count}, "
                        f"content_length={len(full_answer)}"
                    )

            # Final save after the stream finishes.
            if full_answer.strip():
                # Security: Output guardrail
                output_guardrail.validate_or_raise(full_answer)
                
                conversations.update_message(
                    assistant_message.id,
                    content=full_answer,
                    sql=sql,
                )

                print(
                    f"FINAL SAVE: "
                    f"content_length={len(full_answer)}"
                )

        except Exception as error:
            # Record blocked attempt if it's a guardrail error
            error_str = str(error).lower()
            if "blocked" in error_str or "invalid" in error_str:
                reason = "output_guardrail_blocked" if "output" in error_str else "unknown_error"
                rate_limiter.record_blocked_attempt(user_id, reason)
            
            error_message = (
                f"حصل خطأ اثناء توليد الرد: {error}"
            )

            full_answer += f"\n[{error_message}]"

            # Save whatever has been generated before the error.
            conversations.update_message(
                assistant_message.id,
                content=full_answer,
                sql=sql,
            )

            yield f"data: {error_message}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
