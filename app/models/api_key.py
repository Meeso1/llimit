from dataclasses import dataclass
from datetime import datetime


@dataclass
class ApiKey:
    id: str
    user_id: str
    key_hash: str
    name: str
    created_at: datetime
    deleted_at: datetime | None = None

