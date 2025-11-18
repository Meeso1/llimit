from dataclasses import dataclass

from app.services.llm.config.reasoning_config import ReasoningConfig
from app.services.llm.config.web_search_config import WebSearchConfig


@dataclass
class LlmConfig:
    """Configuration for LLM completion requests"""
    web_search: WebSearchConfig
    reasoning: ReasoningConfig

    @classmethod
    def default(cls) -> "LlmConfig":
        """Create a default config (all features disabled)"""
        return cls(
            web_search=WebSearchConfig.default(),
            reasoning=ReasoningConfig.default(),
        )

