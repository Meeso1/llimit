import base64
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.db.file_repo import FileRepo
from app.models.file.models import FileMetadata
from app.services.file_metadata_processing_service import FileMetadataProcessingService
from app.services.llm.llm_file import LlmFileBase, Pdf, PrfUrl, Image, ImageUrl, Audio, Video, VideoUrl, TextFile
from app.settings import settings


# Supported content types for file uploads
SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
SUPPORTED_PDF_TYPES = ["application/pdf"]
SUPPORTED_AUDIO_TYPES = ["audio/wav", "audio/mp3", "audio/mpeg"]
SUPPORTED_VIDEO_TYPES = ["video/mp4", "video/mov", "video/mpeg", "video/webm"]
# Text types support any text/* content type


class FileService:
    """Service for file upload and management"""
    
    def __init__(
        self,
        file_repo: FileRepo,
        file_metadata_processing_service: FileMetadataProcessingService
    ) -> None:
        self._file_repo = file_repo
        self._file_metadata_processing_service = file_metadata_processing_service
        self._uploads_dir = settings.uploads_path
        os.makedirs(self._uploads_dir, exist_ok=True)
    
    def _validate_content_type(self, content_type: str) -> None:
        """Validate that the content type is supported"""
        if content_type in SUPPORTED_IMAGE_TYPES:
            return
        if content_type in SUPPORTED_PDF_TYPES:
            return
        if content_type in SUPPORTED_AUDIO_TYPES:
            return
        if content_type in SUPPORTED_VIDEO_TYPES:
            return
        if content_type.startswith("text/"):
            return
        
        supported_types = (
            SUPPORTED_IMAGE_TYPES +
            SUPPORTED_PDF_TYPES +
            SUPPORTED_AUDIO_TYPES +
            SUPPORTED_VIDEO_TYPES +
            ["text/*"]
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type: {content_type}. Supported types: {', '.join(supported_types)}"
        )
    
    async def upload_file(
        self,
        user_id: str,
        filename: str,
        description: str | None,
        content_type: str,
        file_content: bytes,
        user_additional_data: dict[str, Any] | None = None,
    ) -> FileMetadata:
        """Upload a file and store its metadata"""
        self._validate_content_type(content_type)
        
        file_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        # Create user subdirectory
        user_dir = os.path.join(self._uploads_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # Generate secure storage filename: {user_id}_{timestamp}_{file_id}.txt
        timestamp = now.strftime("%Y%m%d%H%M%S")
        storage_filename = f"{user_id}_{timestamp}_{file_id}.txt"
        storage_path = os.path.join(user_id, storage_filename)
        full_path = os.path.join(self._uploads_dir, storage_path)
        
        # Encode content as base64 and write as text
        base64_content = base64.b64encode(file_content).decode('utf-8')
        with open(full_path, "w") as f:
            f.write(base64_content)
        
        additional_data = dict(user_additional_data) if user_additional_data else {}
        inferred_data = self._file_metadata_processing_service.process_file(
            content_type=content_type,
            file_content=file_content
        )
        additional_data.update(inferred_data)
        
        # Store metadata in database
        file_metadata = self._file_repo.create_file(
            file_id=file_id,
            user_id=user_id,
            filename=filename,
            description=description,
            content_type=content_type,
            created_at=now,
            size_bytes=len(file_content),
            storage_path=storage_path,
            additional_data=additional_data,
        )
        
        return file_metadata
    
    async def register_file_url(
        self,
        user_id: str,
        url: str,
        filename: str,
        description: str | None,
        content_type: str,
        user_additional_data: dict[str, Any] | None = None,
    ) -> FileMetadata:
        """Register a file URL"""
        self._validate_content_type(content_type)
        
        file_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        additional_data = dict(user_additional_data) if user_additional_data else {}
        
        file_metadata = self._file_repo.create_file(
            file_id=file_id,
            user_id=user_id,
            filename=filename,
            description=description,
            content_type=content_type,
            created_at=now,
            url=url,
            additional_data=additional_data,
        )
        
        return file_metadata
    
    def get_file_path(self, file_metadata: FileMetadata) -> str | None:
        """Get the full path to a file on disk"""
        if file_metadata.storage_path is None:
            return None
        
        return os.path.join(self._uploads_dir, file_metadata.storage_path)
    
    def read_file_content(self, file_metadata: FileMetadata) -> bytes | None:
        """Read file content from disk and decode from base64"""
        path = self.get_file_path(file_metadata)
        if path is None or not os.path.exists(path):
            return None
        
        try:
            with open(path, "r") as f:
                base64_content = f.read()
            return base64.b64decode(base64_content)
        except Exception as e:
            print(f"Error reading file content from {path}: {e}")
            return None
    
    def _convert_url_file_to_llm_file(self, file_metadata: FileMetadata) -> LlmFileBase:
        """Convert a URL-based file to an LlmFileBase object"""
        if file_metadata.url is None:
            raise Exception(f"File {file_metadata.id} has no URL")
        
        content_type = file_metadata.content_type
        
        # PDFs, images, and videos can use URLs directly
        # Audio does not support URLs according to OpenRouter docs
        if content_type == "application/pdf":
            return PrfUrl(name=file_metadata.filename, url=file_metadata.url)
        elif content_type.startswith("image/"):
            return ImageUrl(url=file_metadata.url)
        elif content_type.startswith("video/"):
            return VideoUrl(url=file_metadata.url)
        
        # For audio and text, we need the actual content
        raise Exception(f"Unsupported content type: {content_type}")
    
    def _convert_local_file_to_llm_file(self, file_metadata: FileMetadata) -> LlmFileBase:
        """Convert a local/uploaded file to an LlmFileBase object"""
        content = self.read_file_content(file_metadata)
        if content is None:
            raise Exception(f"Failed to read content for file {file_metadata.id}")
        
        content_type = file_metadata.content_type
        
        # Handle different content types
        if content_type == "application/pdf":
            return Pdf(name=file_metadata.filename, content=content)
        elif content_type.startswith("image/"):
            return Image(type=content_type, content=content)
        elif content_type.startswith("audio/"):
            # Extract format from content type (e.g., "audio/wav" -> "wav")
            audio_format = content_type.split("/")[1]
            return Audio(type=audio_format, content=content)
        elif content_type.startswith("video/"):
            return Video(type=content_type, content=content)
        elif content_type.startswith("text/"):
            # Decode text content
            try:
                text_content = content.decode("utf-8")
            except UnicodeDecodeError:
                # Try with latin-1 as fallback
                text_content = content.decode("latin-1")
            return TextFile(
                filename=file_metadata.filename,
                content_type=content_type,
                content=text_content,
            )
        
        raise Exception(f"Unsupported content type: {content_type}")
    
    def convert_file_to_llm_file(self, file_metadata: FileMetadata) -> LlmFileBase:
        """Convert a FileMetadata object to an LlmFileBase object"""
        if file_metadata.url is not None:
            return self._convert_url_file_to_llm_file(file_metadata)
        
        return self._convert_local_file_to_llm_file(file_metadata)

