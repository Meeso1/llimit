from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response as FastAPIResponse

from app.api.dependencies import ChatServiceDep, RequestContextDep
from app.models.chat.requests import (
    CreateChatThreadRequest,
    SendMessageRequest,
    UpdateThreadRequest,
)
from app.models.chat.responses import (
    ChatMessageResponse,
    ChatThreadListResponse,
    ChatThreadResponse,
)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


@router.post("/threads", response_model=ChatThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    request: CreateChatThreadRequest,
    chat_service: ChatServiceDep,
    context: RequestContextDep,
) -> ChatThreadResponse:
    return (await chat_service.create_thread(context.user_id, request)).to_response()


@router.get("/threads", response_model=ChatThreadListResponse)
async def list_threads(
    chat_service: ChatServiceDep,
    context: RequestContextDep,
) -> ChatThreadListResponse:
    threads = await chat_service.list_threads(context.user_id)
    
    return ChatThreadListResponse(
        threads=[t.to_response() for t in threads],
    )


@router.get("/threads/{thread_id}", response_model=ChatThreadResponse)
async def get_thread(
    thread_id: str,
    chat_service: ChatServiceDep,
    context: RequestContextDep,
) -> ChatThreadResponse:
    thread = await chat_service.get_thread(thread_id, context.user_id)
    if thread:
        return thread.to_response()

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Thread not found",
    )


@router.patch("/threads/{thread_id}", response_model=ChatThreadResponse)
async def update_thread(
    thread_id: str,
    request: UpdateThreadRequest,
    chat_service: ChatServiceDep,
    context: RequestContextDep,
) -> ChatThreadResponse:
    thread = await chat_service.update_thread(thread_id, context.user_id, request)
    if thread:
        return thread.to_response()
        
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Thread not found",
    )


@router.post("/threads/{thread_id}/messages", status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    thread_id: str,
    request: SendMessageRequest,
    chat_service: ChatServiceDep,
    context: RequestContextDep,
) -> FastAPIResponse:
    new_message_id = await chat_service.send_message(
        thread_id, 
        context.user_id, 
        request, 
        api_key=context.openrouter_api_key
    )
    if new_message_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )

    return FastAPIResponse(
        status_code=status.HTTP_202_ACCEPTED,
        headers={"Location": new_message_id}
    )


@router.get("/threads/{thread_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    thread_id: str,
    chat_service: ChatServiceDep,
    context: RequestContextDep,
) -> list[ChatMessageResponse]:
    messages = await chat_service.get_messages(thread_id, context.user_id)
    if messages is not None:
        return [m.to_response() for m in messages]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Thread not found",
    )
