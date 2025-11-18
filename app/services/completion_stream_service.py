from typing import AsyncGenerator
from uuid import uuid4

from app.events.completion_events import completion_started, completion_chunk, completion_finished
from app.events.sse_event import SseEvent
from app.services.llm.llm_service_base import LlmMessage, LlmService


class CompletionStreamService:
    def __init__(self, llm_service: LlmService) -> None:
        self._llm_service = llm_service
    
    async def stream_completion(
        self,
        api_key: str,
        model: str,
        messages: list[LlmMessage],
        additional_requested_data: dict[str, str] | None = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[SseEvent, None]:
        completion_id = str(uuid4())
        yield completion_started(completion_id)
        
        async for chunk in self._llm_service.get_completion_streamed(
            api_key=api_key,
            model=model,
            messages=messages,
            additional_requested_data=additional_requested_data,
            temperature=temperature,
            config=None,
        ):
            yield completion_chunk(completion_id, chunk)
        
        yield completion_finished(completion_id)

