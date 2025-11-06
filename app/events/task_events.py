from uuid import uuid4

from app.events.sse_event import SseEvent
from app.models.task.models import Task, TaskStep


def create_task_steps_generated_event(task: Task, steps: list[TaskStep]) -> SseEvent:
    """Create an SSE event when task steps are generated"""
    return SseEvent(
        event_type="task.steps_generated",
        content={
            "task_id": task.id,
            "title": task.title,
            "step_count": len(steps),
        },
        metadata={
            "task_id": task.id,
        },
        event_id=str(uuid4()),
    )


def create_task_step_completed_event(task: Task, step: TaskStep) -> SseEvent:
    """Create an SSE event when a task step is completed"""
    return SseEvent(
        event_type="task.step_completed",
        content={
            "task_id": task.id,
            "step_id": step.id,
            "step_number": step.step_number,
            "response_content": step.response_content,
        },
        metadata={
            "task_id": task.id,
            "step_id": step.id,
        },
        event_id=str(uuid4()),
    )


def create_task_completed_event(task: Task) -> SseEvent:
    """Create an SSE event when the entire task is completed"""
    return SseEvent(
        event_type="task.completed",
        content={
            "task_id": task.id,
            "title": task.title,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        },
        metadata={
            "task_id": task.id,
        },
        event_id=str(uuid4()),
    )


# TODO: Is this needed? Maybe there should be some other way of handling unexpected task results?
def create_task_failed_event(task: Task, error: str) -> SseEvent:
    """Create an SSE event when a task fails"""
    return SseEvent(
        event_type="task.failed",
        content={
            "task_id": task.id,
            "error": error,
        },
        metadata={
            "task_id": task.id,
        },
        event_id=str(uuid4()),
    )

