from dataclasses import dataclass
from enum import Enum


class ReasoningEffort(str, Enum):
    """Reasoning effort level for LLM completions"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"
    NONE = "none"


@dataclass
class ReasoningConfig:
    """Configuration for reasoning/thinking in LLM completions"""
    effort: ReasoningEffort = ReasoningEffort.NONE

    def is_enabled(self) -> bool:
        """Check if reasoning is enabled"""
        return self.effort != ReasoningEffort.NONE

    @classmethod
    def default(cls) -> "ReasoningConfig":
        """Create a default reasoning config (disabled)"""
        return cls()
    
    @classmethod
    def with_medium_effort(cls) -> "ReasoningConfig":
        """Create a reasoning config with medium effort"""
        return cls(effort=ReasoningEffort.MEDIUM)

