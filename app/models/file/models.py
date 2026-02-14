from datetime import datetime
from dataclasses import dataclass
from typing import Literal, get_args

from app.models.file.responses import FileMetadataResponse


ImageType = Literal["jpeg", "png", "gif", "webp"]
AudioType = Literal["wav", "mp3"]
VideoType = Literal["mp4", "mov", "mpeg", "webm"]


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

    def get_image_type(self) -> ImageType | None:
        if not self.content_type.startswith("image/"):
            return None
        
        image_type = self.content_type.split("/")[1]
        if image_type in get_args(ImageType):
            raise ValueError(f"Unsupported image type: {image_type}")

        return image_type

    def get_audio_type(self) -> AudioType | None:
        if not self.content_type.startswith("audio/"):
            return None
        
        audio_type = self.content_type.split("/")[1]
        if audio_type in get_args(AudioType):
            raise ValueError(f"Unsupported audio type: {audio_type}")

        return audio_type

    def get_video_type(self) -> VideoType | None:
        if not self.content_type.startswith("video/"):
            return None

        if self.url is not None:
            return "url"
        
        video_type = self.content_type.split("/")[1]
        if video_type in get_args(VideoType):
            raise ValueError(f"Unsupported video type: {video_type}")

        return video_type

    def is_text_file(self) -> bool:
        return self.content_type.startswith("text/")

    def is_pdf(self) -> bool:
        return self.content_type == "application/pdf"
