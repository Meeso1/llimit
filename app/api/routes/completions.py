from typing import AsyncGenerator
from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import LLMServiceDep, CompletionStreamServiceDep, AuthContextDep
from app.models.completion.requests import CompletionRequest
from app.models.completion.responses import CompletionResponse
from app.services.llm.llm_service_base import LlmMessage

router = APIRouter(
    prefix="/completions",
    tags=["completions"],
)


def _build_messages_from_request(request_body: CompletionRequest) -> list[LlmMessage]:
    """Build LlmMessage list from request, including the prompt as a user message."""
    messages: list[LlmMessage] = []
    if request_body.messages:
        messages = [
            LlmMessage(
                role=msg.role,
                content=msg.content,
                additional_data=msg.additional_data,
            )
            for msg in request_body.messages
        ]
    
    # Append the prompt as a user message
    messages.append(
        LlmMessage(
            role="user",
            content=request_body.prompt,
            additional_data={},
        )
    )
    
    return messages


@router.post("", response_model=CompletionResponse, status_code=status.HTTP_200_OK)
async def create_completion(
    request_body: CompletionRequest,
    context: AuthContextDep(require_openrouter_key=True),
    llm_service: LLMServiceDep,
) -> CompletionResponse:
    """
    Get a completion from the LLM without saving it to any conversation history.
    This is a machine-friendly endpoint for direct LLM interactions.
    """
    messages = _build_messages_from_request(request_body)
    
    response = await llm_service.get_completion(
        api_key=context.openrouter_api_key,
        model=request_body.model,
        messages=messages,
        additional_requested_data=request_body.additional_requested_data,
        temperature=request_body.temperature,
        config=None,
    )
    
    return CompletionResponse(
        role=response.role,
        content=response.content,
        additional_data=response.additional_data,
    )


@router.post("/stream", status_code=status.HTTP_200_OK)
async def create_completion_stream(
    request_body: CompletionRequest,
    context: AuthContextDep(require_openrouter_key=True),
    stream_service: CompletionStreamServiceDep,
) -> StreamingResponse:
    """
    Get a streaming completion from the LLM without saving it to any conversation history.
    This endpoint returns Server-Sent Events (SSE) for real-time streaming.
    """
    
    async def event_generator() -> AsyncGenerator[str, None]:
        messages = _build_messages_from_request(request_body)
        
        # Stream events
        async for event in stream_service.stream_completion(
            api_key=context.openrouter_api_key,
            model=request_body.model,
            messages=messages,
            additional_requested_data=request_body.additional_requested_data,
            temperature=request_body.temperature,
        ):
            yield event.format_sse()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )

