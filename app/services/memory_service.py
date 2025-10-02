from datetime import datetime, timezone
from uuid import uuid4

from app.models.memory.requests import CreateMemoryRequest
from app.models.memory.requests import QueryMemoryRequest
from app.models.memory.responses import MemoryEntry


class MemoryService:
    def __init__(self) -> None:
        self._memories: dict[str, dict] = {}
    
    async def create_memory(self, request: CreateMemoryRequest) -> MemoryEntry:
        memory_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        memory = {
            "id": memory_id,
            "content": request.content,
            "tags": request.tags,
            "created_at": now,
            "updated_at": now,
            "metadata": request.metadata,
        }
        
        self._memories[memory_id] = memory
        
        return MemoryEntry(
            id=memory["id"],
            content=memory["content"],
            tags=memory["tags"],
            created_at=memory["created_at"],
            updated_at=memory["updated_at"],
            metadata=memory["metadata"],
        )
    
    async def get_memory(self, memory_id: str) -> MemoryEntry | None:
        memory = self._memories.get(memory_id)
        if not memory:
            return None
        
        return MemoryEntry(
            id=memory["id"],
            content=memory["content"],
            tags=memory["tags"],
            created_at=memory["created_at"],
            updated_at=memory["updated_at"],
            metadata=memory["metadata"],
        )
    
    async def list_memories(self, limit: int = 50, offset: int = 0) -> tuple[list[MemoryEntry], int]:
        all_memories = sorted(
            self._memories.values(),
            key=lambda m: m["created_at"],
            reverse=True,
        )
        
        page_memories = all_memories[offset:offset + limit]
        
        entries = [
            MemoryEntry(
                id=memory["id"],
                content=memory["content"],
                tags=memory["tags"],
                created_at=memory["created_at"],
                updated_at=memory["updated_at"],
                metadata=memory["metadata"],
            )
            for memory in page_memories
        ]
        
        return entries, len(all_memories)
    
    async def query_memories(self, request: QueryMemoryRequest) -> list[MemoryEntry]:
        results = []
        
        for memory in self._memories.values():
            content_match = request.query.lower() in memory["content"].lower()
            
            tag_match = True
            if request.tags:
                tag_match = any(tag in memory["tags"] for tag in request.tags)
            
            if content_match and tag_match:
                results.append(
                    MemoryEntry(
                        id=memory["id"],
                        content=memory["content"],
                        tags=memory["tags"],
                        created_at=memory["created_at"],
                        updated_at=memory["updated_at"],
                        metadata=memory["metadata"],
                    )
                )
            
            if len(results) >= request.limit:
                break
        
        return results
    
    async def delete_memory(self, memory_id: str) -> bool:
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False
