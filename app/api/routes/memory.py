from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import MemoryServiceDep
from app.middleware.auth import verify_api_key
from app.models.memory.requests import (
    CreateMemoryRequest,
    QueryMemoryRequest,
)
from app.models.memory.responses import (
    MemoryEntry,
    MemoryListResponse,
    MemoryQueryResponse,
)

router = APIRouter(
    prefix="/memory",
    tags=["memory"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=MemoryEntry, status_code=status.HTTP_201_CREATED)
async def create_memory(
    request: CreateMemoryRequest,
    memory_service: MemoryServiceDep,
) -> MemoryEntry:
    return await memory_service.create_memory(request)


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    memory_service: MemoryServiceDep,
    limit: int = Query(50, ge=1, le=100, description="Maximum entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
) -> MemoryListResponse:
    entries, total = await memory_service.list_memories(limit=limit, offset=offset)
    
    return MemoryListResponse(
        entries=entries,
        total=total,
    )


@router.get("/{memory_id}", response_model=MemoryEntry)
async def get_memory(
    memory_id: str,
    memory_service: MemoryServiceDep,
) -> MemoryEntry:
    memory = await memory_service.get_memory(memory_id)
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    return memory


@router.post("/query", response_model=MemoryQueryResponse)
async def query_memories(
    request: QueryMemoryRequest,
    memory_service: MemoryServiceDep,
) -> MemoryQueryResponse:
    results = await memory_service.query_memories(request)
    
    return MemoryQueryResponse(
        results=results,
        query=request.query,
        total_results=len(results),
    )


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: str,
    memory_service: MemoryServiceDep,
) -> None:
    success = await memory_service.delete_memory(memory_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
