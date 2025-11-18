from datetime import datetime
from dataclasses import dataclass

from app.models.file.responses import FileMetadataResponse


@dataclass
class FileMetadata:
    """Represents metadata for an uploaded file"""
    id: str
    user_id: str
    filename: str
    description: str | None
    content_type: str
    size_bytes: int
    storage_path: str
    created_at: datetime

    def to_response(self) -> FileMetadataResponse:
        return FileMetadataResponse(
            id=self.id,
            filename=self.filename,
            description=self.description,
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            created_at=self.created_at,
        )

