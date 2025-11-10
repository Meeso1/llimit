from dataclasses import dataclass
from enum import Enum

from app.models.task.models import Task


class WorkItemType(str, Enum):
    """Type of work item in the queue"""
    DECOMPOSE_TASK = "decompose_task"
    EXECUTE_STEP = "execute_step"


@dataclass
class WorkQueueItem:
    """Represents a work item in the queue"""
    task_id: str
    user_id: str
    item_type: WorkItemType
    step_id: str | None
    api_key: str

    @staticmethod
    def make_task_decomposition_item(task: Task, api_key: str) -> 'WorkQueueItem':
        return WorkQueueItem(
            task_id=task.id,
            user_id=task.user_id,
            item_type=WorkItemType.DECOMPOSE_TASK,
            step_id=None,
            api_key=api_key,
        )
        
    @staticmethod
    def make_task_step_execution_item(task: Task, step_id: str, api_key: str) -> 'WorkQueueItem':
        return WorkQueueItem(
            task_id=task.id,
            user_id=task.user_id,
            item_type=WorkItemType.EXECUTE_STEP,
            step_id=step_id,
            api_key=api_key,
        )
