from datetime import datetime

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    id: str
    content: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)


class MemoryListResponse(BaseModel):
    entries: list[MemoryEntry]
    total: int


class MemoryQueryResponse(BaseModel):
    results: list[MemoryEntry]
    query: str
    total_results: int

