from dataclasses import dataclass, field
from typing import Any

from app.services.llm.llm_file import LlmFileBase


@dataclass
class LlmMessage:
    role: str
    content: str
    additional_data: dict[str, str] = field(default_factory=dict)
    files: list[LlmFileBase] = field(default_factory=list)

    prompt_tokens: int | None = None  # Only set for role="assistant"
    completion_tokens: int | None = None  # Only set for role="assistant"
    
    @staticmethod
    def user(content: str, files: list[LlmFileBase] | None = None) -> "LlmMessage":
        return LlmMessage(role="user", content=content, additional_data={}, files=files or [])
    
    @staticmethod
    def assistant(
        content: str,
        additional_data: dict[str, str] | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> "LlmMessage":
        return LlmMessage(
            role="assistant",
            content=content,
            additional_data=additional_data or {},
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
    
    @staticmethod
    def system(content: str, files: list[LlmFileBase] | None = None) -> "LlmMessage":
        return LlmMessage(role="system", content=content, additional_data={}, files=files or [])
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self._build_content(),
        }
        
    def _build_content(self) -> str | list[dict[str, Any]]:
        if not self.files:
            return self.content
        
        return [
                {
                    "type": "text",
                    "text": self.content
                },
                *[file.to_dict() for file in self.files]
            ]