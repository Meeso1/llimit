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
    FAILED = "failed"

