from datetime import datetime, timezone
from app.db.database import Database, register_schema_sql
from app.models.api_key import ApiKey


@register_schema_sql
def _create_api_keys_table() -> str:
    return """
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            key_hash TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            deleted_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """


@register_schema_sql
def _create_api_keys_index() -> str:
    return """
        CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash 
        ON api_keys(key_hash)
    """


@register_schema_sql
def _create_api_keys_user_index() -> str:
    return """
        CREATE INDEX IF NOT EXISTS idx_api_keys_user_id 
        ON api_keys(user_id)
    """


class ApiKeyRepo:
    def __init__(self, db: Database) -> None:
        self.db = db
    
    def get_api_key_by_hash(self, key_hash: str) -> ApiKey | None:
        rows = self.db.execute_query(
            "SELECT id, user_id, key_hash, name, created_at, deleted_at FROM api_keys WHERE key_hash = ?",
            (key_hash,)
        )
        
        if not rows:
            return None
        
        row = rows[0]
        return ApiKey(
            id=row["id"],
            user_id=row["user_id"],
            key_hash=row["key_hash"],
            name=row["name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
        )
    
    def get_api_key_by_id(self, key_id: str) -> ApiKey | None:
        rows = self.db.execute_query(
            "SELECT id, user_id, key_hash, name, created_at, deleted_at FROM api_keys WHERE id = ?",
            (key_id,)
        )
        
        if not rows:
            return None
        
        row = rows[0]
        return ApiKey(
            id=row["id"],
            user_id=row["user_id"],
            key_hash=row["key_hash"],
            name=row["name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
        )
    
    def list_api_keys_by_user(self, user_id: str, include_deleted: bool = False) -> list[ApiKey]:
        if include_deleted:
            query = "SELECT id, user_id, key_hash, name, created_at, deleted_at FROM api_keys WHERE user_id = ? ORDER BY created_at DESC"
        else:
            query = "SELECT id, user_id, key_hash, name, created_at, deleted_at FROM api_keys WHERE user_id = ? AND deleted_at IS NULL ORDER BY created_at DESC"
        
        rows = self.db.execute_query(query, (user_id,))
        
        return [
            ApiKey(
                id=row["id"],
                user_id=row["user_id"],
                key_hash=row["key_hash"],
                name=row["name"],
                created_at=datetime.fromisoformat(row["created_at"]),
                deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
            )
            for row in rows
        ]
    
    def create_api_key(self, key_id: str, user_id: str, key_hash: str, name: str) -> ApiKey:
        created_at = datetime.now(timezone.utc)
        self.db.execute_update(
            "INSERT INTO api_keys (id, user_id, key_hash, name, created_at, deleted_at) VALUES (?, ?, ?, ?, ?, NULL)",
            (key_id, user_id, key_hash, name, created_at.isoformat())
        )
        
        return ApiKey(
            id=key_id,
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            created_at=created_at,
        )
    
    def soft_delete_api_key(self, key_id: str) -> None:
        self.db.execute_update(
            "UPDATE api_keys SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (datetime.now(timezone.utc).isoformat(), key_id)
        )

