from dataclasses import dataclass, field
from datetime import datetime

from app.models.task.enums import WorkItemType
from app.models.task.models import Task
from app.models.task.responses import WorkQueueItemInfo


@dataclass
class WorkQueueItem:
    """Represents a work item in the queue"""
    task_id: str
    user_id: str
    item_type: WorkItemType
    step_id: str | None
    step_number: int | None
    api_key: str
    enqueue_time: datetime | None = field(default=None)
    start_time: datetime | None = field(default=None)

    def to_response(self) -> WorkQueueItemInfo:
        return WorkQueueItemInfo(
            task_id=self.task_id,
            step_id=self.step_id,
            step_number=self.step_number,
            item_type=self.item_type,
            enqueue_time=self.enqueue_time,
            start_time=self.start_time,
        )

    @staticmethod
    def make_task_decomposition_item(task: Task, api_key: str) -> 'WorkQueueItem':
        return WorkQueueItem(
            task_id=task.id,
            user_id=task.user_id,
            item_type=WorkItemType.DECOMPOSE_TASK,
            step_id=None,
            step_number=None,
            api_key=api_key,
        )

    @staticmethod
    def make_task_step_execution_item(task: Task, step_id: str, step_number: int, api_key: str) -> 'WorkQueueItem':
        return WorkQueueItem(
            task_id=task.id,
            user_id=task.user_id,
            item_type=WorkItemType.EXECUTE_STEP,
            step_id=step_id,
            step_number=step_number,
            api_key=api_key,
        )

    @staticmethod
    def make_task_reevaluation_item(task: Task, step_id: str, step_number: int, api_key: str) -> 'WorkQueueItem':
        return WorkQueueItem(
            task_id=task.id,
            user_id=task.user_id,
            item_type=WorkItemType.REEVALUATE,
            step_id=step_id,
            step_number=step_number,
            api_key=api_key,
        )

