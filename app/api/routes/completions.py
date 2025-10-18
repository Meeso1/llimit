from fastapi import APIRouter, status

from app.api.dependencies import LLMServiceDep, AuthContextDep
from app.models.completion.requests import CompletionRequest
from app.models.completion.responses import CompletionResponse
from app.services.llm_service_base import LlmMessage

router = APIRouter(
    prefix="/completions",
    tags=["completions"],
)


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
    
    response = await llm_service.get_completion(
        api_key=context.openrouter_api_key,
        model=request_body.model,
        messages=messages,
        additional_requested_data=request_body.additional_requested_data,
        temperature=request_body.temperature,
    )
    
    return CompletionResponse(
        role=response.role,
        content=response.content,
        additional_data=response.additional_data,
    )

