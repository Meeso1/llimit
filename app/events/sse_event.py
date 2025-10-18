from dataclasses import dataclass
import json
from typing import Any


@dataclass
class SseEvent:
    event_type: str
    content: Any
    metadata: dict[str, Any]
    event_id: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.event_type,
            "content": self.content,
            "metadata": self.metadata,
            "event_id": self.event_id,
        }
    
    def format_sse(self) -> str:
        data = json.dumps(self.to_dict())
        return f"data: {data}\n\n"