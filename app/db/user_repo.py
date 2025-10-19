from datetime import datetime, timezone
from app.db.database import Database, register_schema_sql
from app.models.user import User


@register_schema_sql
def _create_users_table() -> str:
    return """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        )
    """


class UserRepo:
    """Repository for user data access"""
    
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_user_by_id(self, user_id: str) -> User | None:
        """Get a user by their ID"""
        rows = self.db.execute_query(
            "SELECT id FROM users WHERE id = ?",
            (user_id,)
        )
        
        if not rows:
            return None
        return User(id=rows[0]["id"])

    def create_user(self, user_id: str) -> None:
        """Create a new user"""
        self.db.execute_update(
            "INSERT INTO users (id, created_at) VALUES (?, ?)",
            (user_id, datetime.now(timezone.utc).isoformat())
        )
