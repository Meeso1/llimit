from uuid import uuid4

from app.events.sse_event import SseEvent
from app.services.llm.llm_service_base import StreamedChunk


completion_started_event_type = "completion.started"
completion_chunk_event_type = "completion.chunk"
completion_finished_event_type = "completion.finished"


def completion_started(completion_id: str) -> SseEvent:
    """Create an event for when a completion starts streaming."""
    return SseEvent(
        event_type=completion_started_event_type,
        content={},
        metadata={"completion_id": completion_id},
        event_id=str(uuid4()),
    )


def completion_chunk(completion_id: str, chunk: StreamedChunk) -> SseEvent:
    """Create an event for a chunk of completion content."""
    return SseEvent(
        event_type=completion_chunk_event_type,
        content={
            "content": chunk.content,
            "additional_data_key": chunk.additional_data_key,
        },
        metadata={"completion_id": completion_id},
        event_id=str(uuid4()),
    )


def completion_finished(completion_id: str) -> SseEvent:
    """Create an event for when a completion finishes streaming."""
    return SseEvent(
        event_type=completion_finished_event_type,
        content={},
        metadata={"completion_id": completion_id},
        event_id=str(uuid4()),
    )

