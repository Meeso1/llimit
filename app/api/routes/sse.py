from uuid import uuid4
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from app.api.dependencies import AuthContextDep, SseServiceDep
from app.events.sse_event import SseEvent
from app.services.sse_service import EventFilter


router = APIRouter(
    prefix="/sse",
    tags=["sse"],
)


@router.get("/events")
async def stream_events(
    request: Request,
    context: AuthContextDep(require_openrouter_key=False),
    sse_service: SseServiceDep,
    event_types: list[str] | None = Query(
        None,
        description="Filter by event types. If not specified, all event types are included.",
    ),
) -> StreamingResponse:
    """
    Stream Server-Sent Events to the client.
    Events are user-specific and will only include events for the authenticated user.
    
    Query parameters:
    - event_types: List of event types to filter (e.g., ?event_types=type1&event_types=type2)
    - Any other query parameter: Treated as metadata filter (e.g., ?thread_id=abc&thread_id=def)
    
    Examples:
    - ?event_types=message.new_from_assistant - Only assistant messages
    - ?thread_id=abc123 - Only events from thread abc123
    - ?thread_id=abc&thread_id=def - Events from threads abc or def
    - ?event_types=message.new_from_assistant&thread_id=abc - Assistant messages from thread abc
    
    If no filters are specified, all events for the user will be streamed.
    """
    
    async def event_generator() -> AsyncGenerator[str, None]:
        # Build metadata filters from all query parameters except event_types
        metadata_filters = {}
        for key, values in request.query_params.multi_items():
            if key != "event_types":
                if key not in metadata_filters:
                    metadata_filters[key] = []
                metadata_filters[key].append(values)
        
        event_filter = EventFilter(
            event_types=event_types,
            metadata_filters=metadata_filters if metadata_filters else None,
        )
        
        # Register connection for this user with filter
        connection = await sse_service.register_connection(context.user_id, event_filter)
        
        try:
            yield SseEvent(
                event_type="connection.established",
                content={"connection_id": connection.connection_id},
                metadata={},
                event_id=str(uuid4()),
            ).format_sse()
            
            while True:
                event = await connection.receive()
                yield event.format_sse()
        except Exception as e:
            print(f"SSE connection error: {e}")
        finally:
            await sse_service.unregister_connection(connection)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )

