from datetime import datetime

from app.db.database import Database, register_schema_sql
from app.models.file.models import FileMetadata


@register_schema_sql
def _create_files_table() -> str:
    return """
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            description TEXT,
            content_type TEXT NOT NULL,
            size_bytes INTEGER,
            storage_path TEXT,
            url TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """


@register_schema_sql
def _create_files_user_index() -> str:
    return """
        CREATE INDEX IF NOT EXISTS idx_files_user_id 
        ON files(user_id)
    """


class FileRepo:
    """Repository for file metadata access"""
    
    def __init__(self, db: Database) -> None:
        self.db = db
    
    def create_file(
        self,
        file_id: str,
        user_id: str,
        filename: str,
        description: str | None,
        content_type: str,
        created_at: datetime,
        size_bytes: int | None = None,
        storage_path: str | None = None,
        url: str | None = None,
    ) -> FileMetadata:
        """Create a new file metadata record"""
        self.db.execute_update(
            """
            INSERT INTO files 
            (id, user_id, filename, description, content_type, size_bytes, storage_path, url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                user_id,
                filename,
                description,
                content_type,
                size_bytes,
                storage_path,
                url,
                created_at.isoformat(),
            ),
        )
        
        return FileMetadata(
            id=file_id,
            user_id=user_id,
            filename=filename,
            description=description,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            url=url,
            created_at=created_at,
        )
    
    def get_file_by_id_and_user(self, file_id: str, user_id: str) -> FileMetadata | None:
        """Get a file by ID for a specific user"""
        rows = self.db.execute_query(
            """
            SELECT id, user_id, filename, description, content_type, size_bytes, storage_path, url, created_at
            FROM files
            WHERE id = ? AND user_id = ?
            """,
            (file_id, user_id),
        )
        
        if not rows:
            return None
        
        return self._row_to_file_metadata(rows[0])
    
    def list_files_by_user(self, user_id: str) -> list[FileMetadata]:
        """List all files for a specific user"""
        rows = self.db.execute_query(
            """
            SELECT id, user_id, filename, description, content_type, size_bytes, storage_path, url, created_at
            FROM files
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        
        return [self._row_to_file_metadata(row) for row in rows]
    
    def _row_to_file_metadata(self, row: dict) -> FileMetadata:
        """Convert a database row to a FileMetadata object"""
        return FileMetadata(
            id=row["id"],
            user_id=row["user_id"],
            filename=row["filename"],
            description=row["description"],
            content_type=row["content_type"],
            size_bytes=row["size_bytes"],
            storage_path=row["storage_path"],
            url=row["url"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

