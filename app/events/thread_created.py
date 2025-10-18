from uuid import uuid4

from app.events.sse_event import SseEvent
from app.models.chat.models import ChatThread


thread_created_event_type = "thread.created"

def thread_created(
    thread: ChatThread,
) -> SseEvent:
    return SseEvent(
        event_type=thread_created_event_type,
        content={
            "thread_id": thread.id,
            "title": thread.title,
            "description": thread.description,
            "model_name": thread.model_name,
            "created_at": thread.created_at.isoformat(),
        },
        metadata={},
        event_id=str(uuid4()),
    )