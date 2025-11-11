import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime

from app.db.api_key_repo import ApiKeyRepo
from app.models.api_key import ApiKey


@dataclass
class ApiKeyCreationResult:
    key_id: str
    plaintext_key: str
    name: str
    created_at: datetime


class ApiKeyService:
    def __init__(self, api_key_repo: ApiKeyRepo) -> None:
        self.api_key_repo = api_key_repo
    
    def hash_key(self, plaintext_key: str) -> str:
        """Hash an API key using SHA-256"""
        return hashlib.sha256(plaintext_key.encode()).hexdigest()
    
    def generate_api_key(self) -> str:
        return f"llimit_{secrets.token_urlsafe(32)}"
    
    def create_api_key(self, user_id: str, name: str, key_value: str | None = None) -> ApiKeyCreationResult:
        key_id = str(uuid.uuid4())
        plaintext_key = key_value or self.generate_api_key()
        key_hash = self.hash_key(plaintext_key)
        
        new_api_key = self.api_key_repo.create_api_key(
            key_id=key_id,
            user_id=user_id,
            key_hash=key_hash,
            name=name,
        )
        
        return ApiKeyCreationResult(
            key_id=new_api_key.id,
            plaintext_key=plaintext_key,
            name=new_api_key.name,
            created_at=new_api_key.created_at,
        )
    
    def validate_api_key(self, plaintext_key: str) -> tuple[ApiKey | None, str | None]:
        key_hash = self.hash_key(plaintext_key)
        api_key = self.api_key_repo.get_api_key_by_hash(key_hash)
        
        if api_key is None:
            return None, "Invalid API key"
        
        if api_key.deleted_at is not None:
            return None, "API key has been deleted"
        
        return api_key, None
    
    def delete_api_key(self, key_id: str) -> None:
        self.api_key_repo.soft_delete_api_key(key_id)
    
    def list_user_api_keys(self, user_id: str, include_deleted: bool = False) -> list[ApiKey]:
        return self.api_key_repo.list_api_keys_by_user(user_id, include_deleted)
    
    def get_api_key_by_id(self, key_id: str) -> ApiKey | None:
        return self.api_key_repo.get_api_key_by_id(key_id)

