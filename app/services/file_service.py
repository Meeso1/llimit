import base64
import os
from datetime import datetime, timezone
from uuid import uuid4

from app.db.file_repo import FileRepo
from app.models.file.models import FileMetadata
from app.settings import settings


class FileService:
    """Service for file upload and management"""
    
    def __init__(self, file_repo: FileRepo) -> None:
        self._file_repo = file_repo
        self._uploads_dir = settings.uploads_path
        os.makedirs(self._uploads_dir, exist_ok=True)
    
    async def upload_file(
        self,
        user_id: str,
        filename: str,
        description: str | None,
        content_type: str,
        file_content: bytes,
    ) -> FileMetadata:
        """Upload a file and store its metadata"""
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
        
        # Store metadata in database
        file_metadata = self._file_repo.create_file(
            file_id=file_id,
            user_id=user_id,
            filename=filename,
            description=description,
            content_type=content_type,
            size_bytes=len(file_content),
            storage_path=storage_path,
            created_at=now,
        )
        
        return file_metadata
    
    def get_file_path(self, file_metadata: FileMetadata) -> str:
        """Get the full path to a file on disk"""
        return os.path.join(self._uploads_dir, file_metadata.storage_path)
    
    def read_file_content(self, file_metadata: FileMetadata) -> bytes | None:
        """Read file content from disk and decode from base64"""
        path = self.get_file_path(file_metadata)
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, "r") as f:
                base64_content = f.read()
            return base64.b64decode(base64_content)
        except Exception as e:
            print(f"Error reading file content from {path}: {e}")
            return None

