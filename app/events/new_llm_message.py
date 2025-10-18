from uuid import uuid4
from app.events.sse_event import SseEvent
from app.models.chat.models import ChatMessage


new_llm_message_event_type = "message.new_from_assistant"

def new_llm_message(
    thread_id: str,
    message: ChatMessage,
) -> SseEvent:
    return SseEvent(
        event_type=new_llm_message_event_type,
        content={
            "thread_id": thread_id,
            "message_id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        },
        metadata={
            "thread_id": thread_id,
        },
        event_id=str(uuid4()),
    )