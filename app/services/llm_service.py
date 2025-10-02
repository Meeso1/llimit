from typing import AsyncGenerator


class LLMService:
    def __init__(self) -> None:
        pass
    
    async def generate_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        last_user_message = next(
            (msg["content"] for msg in reversed(messages) if msg["role"] == "user"),
            "Hello",
        )
        return f"Mock LLM response to: {last_user_message[:50]}..."
    
    async def generate_completion_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        last_user_message = next(
            (msg["content"] for msg in reversed(messages) if msg["role"] == "user"),
            "Hello",
        )
        
        response = f"Mock streaming response to: {last_user_message[:30]}..."
        
        for word in response.split():
            yield word + " "
    
    async def generate_title(self, conversation_content: str) -> str:
        preview = conversation_content[:50].strip()
        return f"Conversation about {preview}..."
    
    async def generate_description(self, conversation_content: str) -> str:
        return f"A conversation discussing various topics. Length: {len(conversation_content)} chars."
