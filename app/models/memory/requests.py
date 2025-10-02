from pydantic import BaseModel, Field


class CreateMemoryRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Memory content")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata")


class QueryMemoryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    tags: list[str] = Field(default_factory=list, description="Filter by tags")

