class TaskError(Exception):
    """Base class for task-processing errors."""

    def __init__(self, message: str, should_reevaluate: bool) -> None:
        super().__init__(message)
        self.should_reevaluate = should_reevaluate


class TaskModelSelectionError(TaskError):
    """Raised when a suitable model cannot be selected for a task step."""
    pass


class TaskStepExecutionError(TaskError):
    """Raised when a task step cannot be executed due to an internal error."""
    pass
