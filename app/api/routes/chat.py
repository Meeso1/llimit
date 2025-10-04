from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response as FastAPIResponse

from app.api.dependencies import ChatServiceDep
from app.middleware.auth import verify_api_key
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
    dependencies=[Depends(verify_api_key)],
)


@router.post("/threads", response_model=ChatThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    request: CreateChatThreadRequest,
    chat_service: ChatServiceDep,
) -> ChatThreadResponse:
    return await chat_service.create_thread(request)


@router.get("/threads", response_model=ChatThreadListResponse)
async def list_threads(
    chat_service: ChatServiceDep,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ChatThreadListResponse:
    threads, total = await chat_service.list_threads(page=page, page_size=page_size)
    
    return ChatThreadListResponse(
        threads=threads,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/threads/{thread_id}", response_model=ChatThreadResponse)
async def get_thread(
    thread_id: str,
    chat_service: ChatServiceDep,
) -> ChatThreadResponse:
    thread = await chat_service.get_thread(thread_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )
    return thread


@router.patch("/threads/{thread_id}", response_model=ChatThreadResponse)
async def update_thread(
    thread_id: str,
    request: UpdateThreadRequest,
    chat_service: ChatServiceDep,
) -> ChatThreadResponse:
    thread = await chat_service.update_thread(thread_id, request)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )
    return thread


@router.post("/threads/{thread_id}/messages", status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    thread_id: str,
    request: SendMessageRequest,
    chat_service: ChatServiceDep,
) -> FastAPIResponse:
    new_message_id = await chat_service.send_message(thread_id, request)
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
) -> list[ChatMessageResponse]:
    messages = await chat_service.get_messages(thread_id)
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )
    return messages
