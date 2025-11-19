from dataclasses import dataclass, field


@dataclass
class LlmMessage:
    role: str
    content: str
    additional_data: dict[str, str] = field(default_factory=dict)
    
    @staticmethod
    def user(content: str) -> "LlmMessage":
        return LlmMessage(role="user", content=content, additional_data={})
    
    @staticmethod
    def assistant(content: str, additional_data: dict[str, str] | None = None) -> "LlmMessage":
        return LlmMessage(role="assistant", content=content, additional_data=additional_data or {})
    
    @staticmethod
    def system(content: str) -> "LlmMessage":
        return LlmMessage(role="system", content=content, additional_data={})