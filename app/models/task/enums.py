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


class ModelCapability(str, Enum):
    REASONING = "reasoning"
    WEB_SEARCH = "web_search"
    IMAGE_INPUT = "image_input"
    FILE_INPUT = "file_input"
