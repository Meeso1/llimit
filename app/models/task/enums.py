from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    DECOMPOSING = "decomposing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"  # Failed due to exception/error
    COULD_NOT_COMPLETE = "could_not_complete"  # Failed due to model's inability to complete (non-exception)
    ABANDONED = "abandoned"


class StepType(str, Enum):
    NORMAL = "normal"
    REEVALUATE = "reevaluate"


class ComplexityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# TODO: Add PDF capabilities - native, PDF-text, mistral-OCR
class ModelCapability(str, Enum):
    REASONING = "reasoning"
    EXA_SEARCH = "exa_search"
    NATIVE_WEB_SEARCH = "native_web_search"
    IMAGE_INPUT = "image_input"
    FILE_INPUT = "file_input"

    @staticmethod
    def descriptions() -> dict[str, str]:
        """Returns descriptions for each model capability."""
        return {
            ModelCapability.REASONING.value: "Internal reasoning/thinking generation before response",
            ModelCapability.EXA_SEARCH.value: "Web search based on prompt. It is run **BEFORE** LLM is called, and its result is provided to LLM as context.",
            ModelCapability.NATIVE_WEB_SEARCH.value: "Model-native web search. It can be used by LLM with a generated query. Therefore, it can be used for more specific cases, where search query is different than the prompt.",
        }
