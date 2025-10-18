import asyncio
from collections import defaultdict
from typing import Any
from uuid import uuid4

from app.events.sse_event import SseEvent


class EventFilter:
    def __init__(
        self,
        event_types: list[str] | None = None,
        metadata_filters: dict[str, list[Any]] | None = None,
    ) -> None:
        """
        Initialize event filter.
        
        Args:
            event_types: List of allowed event types, None means all types
            metadata_filters: Dict of metadata key -> list of allowed values
                             e.g. {"thread_id": ["id1", "id2"]}
                             None or empty list for a key means all values allowed
        """
        self.event_types = event_types
        self.metadata_filters = metadata_filters or {}
    
    def matches(self, event: SseEvent) -> bool:
        if self.event_types is not None and event.event_type not in self.event_types:
            return False
        
        for key, allowed_values in self.metadata_filters.items():
            if allowed_values:  # Only filter if list is not empty
                event_value = event.metadata.get(key)
                if event_value is not None and event_value not in allowed_values:
                    return False
        
        return True


class SseConnection:
    def __init__(self, user_id: str, event_filter: EventFilter | None = None) -> None:
        self.user_id = user_id
        self.queue: asyncio.Queue[SseEvent] = asyncio.Queue()
        self.connection_id = str(uuid4())
        self.filter = event_filter or EventFilter()
    
    async def send(self, event: SseEvent) -> None:
        if self.filter.matches(event):
            await self.queue.put(event)
    
    async def receive(self) -> SseEvent:
        return await self.queue.get()


class SseService:
    def __init__(self) -> None:
        # Map of user_id -> list of active connections
        self._connections: dict[str, list[SseConnection]] = defaultdict(list)
        self._user_locks: dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()  # Lock for creating per-user locks
    
    async def _get_user_lock(self, user_id: str) -> asyncio.Lock:
        async with self._locks_lock:
            if user_id not in self._user_locks:
                self._user_locks[user_id] = asyncio.Lock()
            return self._user_locks[user_id]
    
    async def register_connection(
        self,
        user_id: str,
        event_filter: EventFilter | None = None,
    ) -> SseConnection:
        connection = SseConnection(user_id, event_filter)
        user_lock = await self._get_user_lock(user_id)
        async with user_lock:
            self._connections[user_id].append(connection)
        return connection
    
    async def unregister_connection(self, connection: SseConnection) -> None:
        """Unregister an SSE connection"""
        user_lock = await self._get_user_lock(connection.user_id)
        async with user_lock:
            if connection.user_id in self._connections:
                self._connections[connection.user_id] = [
                    conn for conn in self._connections[connection.user_id]
                    if conn.connection_id != connection.connection_id
                ]
                # Clean up empty lists
                if not self._connections[connection.user_id]:
                    del self._connections[connection.user_id]
                    # Clean up the lock as well
                    async with self._locks_lock:
                        if connection.user_id in self._user_locks:
                            del self._user_locks[connection.user_id]
    
    async def emit_event(
        self,
        user_id: str,
        event: SseEvent,
    ) -> None:
        user_lock = await self._get_user_lock(user_id)
        async with user_lock:
            connections = self._connections.get(user_id, [])
            for connection in connections:
                try:
                    await connection.send(event)
                except Exception as e:
                    print(f"Error sending event to connection {connection.connection_id}: {e}")
    
    def get_active_connections_count(self, user_id: str) -> int:
        return len(self._connections.get(user_id, []))

