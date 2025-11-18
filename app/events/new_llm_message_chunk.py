from uuid import uuid4
from app.events.sse_event import SseEvent
from app.services.llm.llm_service_base import StreamedChunk


new_llm_message_chunk_event_type = "message.new_from_assistant_chunk"

def new_llm_message_chunk(
    thread_id: str,
    message_id: str,
    chunk: StreamedChunk,
) -> SseEvent:
    return SseEvent(
        event_type=new_llm_message_chunk_event_type,
        content={
            "content": chunk.content,
            "additional_data_key": chunk.additional_data_key,
        },
        metadata={
            "thread_id": thread_id,
            "message_id": message_id,            
        },
        event_id=str(uuid4()),
    )