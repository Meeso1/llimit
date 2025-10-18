from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response as FastAPIResponse

from app.api.dependencies import ChatServiceDep, AuthServiceDep
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
    request_body: CreateChatThreadRequest,
    request: Request,
    chat_service: ChatServiceDep,
    auth_service: AuthServiceDep,
) -> ChatThreadResponse:
    context = auth_service.authenticate(request, require_openrouter_key=False)
    return (await chat_service.create_thread(context.user_id, request_body)).to_response()


@router.get("/threads", response_model=ChatThreadListResponse)
async def list_threads(
    request: Request,
    chat_service: ChatServiceDep,
    auth_service: AuthServiceDep,
) -> ChatThreadListResponse:
    context = auth_service.authenticate(request, require_openrouter_key=False)
    threads = await chat_service.list_threads(context.user_id)
    
    return ChatThreadListResponse(
        threads=[t.to_response() for t in threads],
    )


@router.get("/threads/{thread_id}", response_model=ChatThreadResponse)
async def get_thread(
    thread_id: str,
    request: Request,
    chat_service: ChatServiceDep,
    auth_service: AuthServiceDep,
) -> ChatThreadResponse:
    context = auth_service.authenticate(request, require_openrouter_key=False)
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
    request_body: UpdateThreadRequest,
    request: Request,
    chat_service: ChatServiceDep,
    auth_service: AuthServiceDep,
) -> ChatThreadResponse:
    context = auth_service.authenticate(request, require_openrouter_key=False)
    thread = await chat_service.update_thread(thread_id, context.user_id, request_body)
    if thread:
        return thread.to_response()
        
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Thread not found",
    )


@router.post("/threads/{thread_id}/messages", status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    thread_id: str,
    request_body: SendMessageRequest,
    request: Request,
    chat_service: ChatServiceDep,
    auth_service: AuthServiceDep,
) -> FastAPIResponse:
    context = auth_service.authenticate(request, require_openrouter_key=True)
    new_message_id = await chat_service.send_message(
        thread_id, 
        context.user_id, 
        request_body, 
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
    request: Request,
    chat_service: ChatServiceDep,
    auth_service: AuthServiceDep,
) -> list[ChatMessageResponse]:
    context = auth_service.authenticate(request, require_openrouter_key=False)
    messages = await chat_service.get_messages(thread_id, context.user_id)
    if messages is not None:
        return [m.to_response() for m in messages]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Thread not found",
    )
