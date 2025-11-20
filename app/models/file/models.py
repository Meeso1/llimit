from datetime import datetime
from dataclasses import dataclass

from app.models.file.responses import FileMetadataResponse


@dataclass
class FileMetadata:
    """Represents metadata for an uploaded file or URL"""
    id: str
    user_id: str
    filename: str
    description: str | None
    content_type: str
    created_at: datetime
    size_bytes: int | None = None
    storage_path: str | None = None
    url: str | None = None

    def to_response(self) -> FileMetadataResponse:
        return FileMetadataResponse(
            id=self.id,
            filename=self.filename,
            description=self.description,
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            url=self.url,
            created_at=self.created_at,
        )

    def get_required_modalities(self) -> list[str]:
        """Get the required modalities for the file"""
        if self.content_type.startswith("image/"):
            return ["image"]
        elif self.content_type.startswith("audio/"):
            return ["audio"]
        elif self.content_type.startswith("video/"):
            return ["video"]

        return []

