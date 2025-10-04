from datetime import datetime, timezone

from app.db.database import Database
from app.models.chat.models import ChatThread, ChatMessage


class ChatRepo:
    """Repository for chat thread and message data access"""
    
    def __init__(self, db: Database) -> None:
        self.db = db
    
    def create_thread(
        self,
        thread_id: str,
        user_id: str,
        title: str | None,
        description: str | None,
        model_name: str,
        created_at: datetime,
    ) -> ChatThread:
        """Create a new chat thread"""
        self.db.execute_update(
            """
            INSERT INTO chat_threads 
            (id, user_id, title, description, created_at, updated_at, model_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                thread_id,
                user_id,
                title,
                description,
                created_at.isoformat(),
                created_at.isoformat(),
                model_name,
            ),
        )
        
        return ChatThread(
            id=thread_id,
            user_id=user_id,
            title=title,
            description=description,
            created_at=created_at,
            updated_at=created_at,
            deleted_at=None,
            model_name=model_name,
            message_count=0,
        )
    
    def get_thread_by_id_and_user(self, thread_id: str, user_id: str) -> ChatThread | None:
        """Get a thread by ID for a specific user"""
        rows = self.db.execute_query(
            """
            SELECT 
                id, user_id, title, description, created_at, updated_at, 
                deleted_at, model_name,
                (SELECT COUNT(*) FROM chat_messages WHERE thread_id = chat_threads.id) as message_count
            FROM chat_threads
            WHERE id = ? AND user_id = ? AND deleted_at IS NULL
            """,
            (thread_id, user_id),
        )
        
        if not rows:
            return None
        
        return self._row_to_thread(rows[0])
    
    def list_threads_by_user(self, user_id: str) -> list[ChatThread]:
        """List all threads for a specific user"""
        rows = self.db.execute_query(
            """
            SELECT 
                id, user_id, title, description, created_at, updated_at, 
                deleted_at, model_name,
                (SELECT COUNT(*) FROM chat_messages WHERE thread_id = chat_threads.id) as message_count
            FROM chat_threads
            WHERE user_id = ? AND deleted_at IS NULL
            ORDER BY updated_at DESC
            """,
            (user_id,),
        )
        
        return [self._row_to_thread(row) for row in rows]
    
    def update_thread(
        self,
        thread_id: str,
        user_id: str,
        title: str | None = None,
        description: str | None = None,
    ) -> ChatThread | None:
        """Update a thread's metadata"""
        # First, get the thread to ensure it exists and belongs to user
        thread = self.get_thread_by_id_and_user(thread_id, user_id)
        if not thread:
            return None
        
        # Build update query dynamically based on what's being updated
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if not updates:
            # Nothing to update
            return thread
        
        # Add updated_at
        now = datetime.now(timezone.utc)
        updates.append("updated_at = ?")
        params.append(now.isoformat())
        
        # Add WHERE clause params
        params.extend([thread_id, user_id])
        
        self.db.execute_update(
            f"UPDATE chat_threads SET {', '.join(updates)} WHERE id = ? AND user_id = ?",
            tuple(params),
        )
        
        # Return updated thread
        return self.get_thread_by_id_and_user(thread_id, user_id)
    
    def add_message(
        self,
        message_id: str,
        thread_id: str,
        role: str,
        content: str,
        created_at: datetime,
    ) -> None:
        """Add a message to a thread"""
        self.db.execute_update(
            """
            INSERT INTO chat_messages (id, thread_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, thread_id, role, content, created_at.isoformat()),
        )
        
        # Update thread's updated_at
        self.db.execute_update(
            "UPDATE chat_threads SET updated_at = ? WHERE id = ?",
            (created_at.isoformat(), thread_id),
        )
    
    def get_messages(self, thread_id: str, user_id: str) -> list[ChatMessage] | None:
        """Get all messages for a thread (only if user owns the thread)"""
        # First verify the thread exists and belongs to the user
        thread = self.get_thread_by_id_and_user(thread_id, user_id)
        if not thread:
            return None
        
        rows = self.db.execute_query(
            """
            SELECT id, role, content, created_at
            FROM chat_messages
            WHERE thread_id = ?
            ORDER BY created_at ASC
            """,
            (thread_id,),
        )
        
        return [
            ChatMessage(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]
    
    def _row_to_thread(self, row: dict) -> ChatThread:
        """Convert a database row to a ChatThread object"""
        return ChatThread(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
            model_name=row["model_name"],
            message_count=row["message_count"],
        )

