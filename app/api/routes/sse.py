from uuid import uuid4
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from app.api.dependencies import AuthContextDep, SseServiceDep
from app.events.sse_event import SseEvent


router = APIRouter(
    prefix="/sse",
    tags=["sse"],
)


@router.get("/events")
async def stream_events(
    context: AuthContextDep(require_openrouter_key=False),
    sse_service: SseServiceDep,
) -> StreamingResponse:
    """
    Stream Server-Sent Events to the client.
    Events are user-specific and will only include events for the authenticated user.
    """
    
    async def event_generator() -> AsyncGenerator[str, None]:
        connection = await sse_service.register_connection(context.user_id)
        
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

