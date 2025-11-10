from datetime import datetime, timezone
from uuid import uuid4

from app.db.task_repo import TaskRepo
from app.models.task.models import Task
from app.models.task.requests import CreateTaskRequest
from app.models.task.work_queue import WorkQueueItem, WorkItemType
from app.services.work_queue_service import WorkQueueService


class TaskCreationService:
    def __init__(
        self,
        task_repo: TaskRepo,
        work_queue_service: WorkQueueService,
    ) -> None:
        self.task_repo = task_repo
        self.work_queue_service = work_queue_service
    
    async def create_task(
        self,
        user_id: str,
        request: CreateTaskRequest,
        api_key: str,
    ) -> Task:        
        task = self.task_repo.create_task(
            task_id=str(uuid4()),
            user_id=user_id,
            prompt=request.prompt,
            created_at=datetime.now(timezone.utc),
        )
        
        await self.work_queue_service.enqueue(WorkQueueItem.make_task_decomposition_item(task, api_key))
        
        return task
    