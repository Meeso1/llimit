import asyncio
from collections import defaultdict
from uuid import uuid4

from app.events.sse_event import SseEvent


class SseConnection:
    """Represents a single SSE connection"""
    
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.queue: asyncio.Queue[SseEvent] = asyncio.Queue()
        self.connection_id = str(uuid4())
    
    async def send(self, event: SseEvent) -> None:
        """Send an event to this connection"""
        await self.queue.put(event)
    
    async def receive(self) -> SseEvent:
        """Receive the next event"""
        return await self.queue.get()


class SseService:
    """Service for managing SSE connections and emitting events"""
    
    def __init__(self) -> None:
        # Map of user_id -> list of active connections
        self._connections: dict[str, list[SseConnection]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def register_connection(self, user_id: str) -> SseConnection:
        """Register a new SSE connection for a user"""
        connection = SseConnection(user_id)
        async with self._lock:
            self._connections[user_id].append(connection)
        return connection
    
    async def unregister_connection(self, connection: SseConnection) -> None:
        """Unregister an SSE connection"""
        async with self._lock:
            if connection.user_id in self._connections:
                self._connections[connection.user_id] = [
                    conn for conn in self._connections[connection.user_id]
                    if conn.connection_id != connection.connection_id
                ]
                # Clean up empty lists
                if not self._connections[connection.user_id]:
                    del self._connections[connection.user_id]
    
    async def emit_event(
        self,
        user_id: str,
        event: SseEvent,
    ) -> None:
        """
        Emit an event to all connections for a specific user.
        
        Args:
            user_id: The user to send the event to
            event_type: The type of event (e.g., "message.created", "chunk.received")
            content: The content/payload of the event
            metadata: Optional metadata (e.g., {"thread_id": "...", "message_id": "..."})
        """
        
        async with self._lock:
            connections = self._connections.get(user_id, [])
            for connection in connections:
                try:
                    await connection.send(event)
                except Exception as e:
                    print(f"Error sending event to connection {connection.connection_id}: {e}")
    
    def get_active_connections_count(self, user_id: str) -> int:
        return len(self._connections.get(user_id, []))

