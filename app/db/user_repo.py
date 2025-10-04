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

