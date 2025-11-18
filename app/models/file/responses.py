from datetime import datetime
from pydantic import BaseModel


class FileMetadataResponse(BaseModel):
    """Response containing file metadata"""
    id: str
    filename: str
    description: str | None
    content_type: str
    size_bytes: int
    created_at: datetime


class FileListResponse(BaseModel):
    """Response containing a list of files"""
    files: list[FileMetadataResponse]

