from dataclasses import dataclass


@dataclass
class User:
    id: str

class UserService:
    """Service for managing users and API key mappings"""
    
    def __init__(self) -> None:
        # TODO: Replace with database
        self._api_key_to_user: dict[str, User] = {
            "test-api-key-1": User(id="user-1"),
            "test-api-key-2": User(id="user-2"),
        }
    
    def get_user_by_api_key(self, api_key: str) -> User | None:
        """Get user by their API key"""
        return self._api_key_to_user.get(api_key)

