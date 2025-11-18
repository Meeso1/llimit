from dataclasses import dataclass
from enum import Enum


class SearchContextSize(str, Enum):
    """Search context size for native web search"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class WebSearchConfig:
    """Configuration for web search in LLM completions"""
    use_exa_search: bool = False
    use_native_search: bool = False
    max_results: int = 5  # For Exa search
    search_context_size: SearchContextSize = SearchContextSize.MEDIUM  # For native search
    search_prompt: str | None = None  # Custom search prompt for Exa search

    def is_enabled(self) -> bool:
        """Check if any web search is enabled"""
        return self.use_exa_search or self.use_native_search

    @classmethod
    def default(cls) -> "WebSearchConfig":
        """Create a default web search config (disabled)"""
        return cls()
