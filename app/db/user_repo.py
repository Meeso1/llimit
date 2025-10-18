from datetime import datetime, timezone
from app.db.database import Database
from app.models.user import User


class UserRepo:
    """Repository for user data access"""
    
    def __init__(self, db: Database) -> None:
        self.db = db
    
    def get_user_by_api_key(self, api_key: str) -> User | None:
        """Get user by their API key"""
        rows = self.db.execute_query(
            "SELECT id FROM users WHERE api_key = ?",
            (api_key,)
        )
        
        if not rows:
            return None
        
        row = rows[0]
        return User(id=row["id"])

    def get_user_by_id(self, user_id: str) -> User | None:
        """Get a user by their ID"""
        rows = self.db.execute_query(
            "SELECT id FROM users WHERE id = ?",
            (user_id,)
        )
        
        if not rows:
            return None
        return User(id=rows[0]["id"])

    def create_user(self, user_id: str, api_key: str) -> None:
        """Create a new user"""
        self.db.execute_update(
            "INSERT INTO users (id, api_key, created_at) VALUES (?, ?, ?)",
            (user_id, api_key, datetime.now(timezone.utc).isoformat())
        )
