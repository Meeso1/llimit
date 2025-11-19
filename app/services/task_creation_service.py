from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from app.db.file_repo import FileRepo
from app.db.task_repo import TaskRepo
from app.events.task_events import create_task_created_event
from app.models.task.models import Task
from app.models.task.requests import CreateTaskRequest
from app.models.task.work_queue import WorkQueueItem
from app.services.sse_service import SseService
from app.services.work_queue_service import WorkQueueService


class TaskCreationService:
    def __init__(
        self,
        task_repo: TaskRepo,
        file_repo: FileRepo,
        work_queue_service: WorkQueueService,
        sse_service: SseService,
    ) -> None:
        self.task_repo = task_repo
        self.file_repo = file_repo
        self.work_queue_service = work_queue_service
        self.sse_service = sse_service
    
    def _validate_file_ids(self, user_id: str, file_ids: list[str]) -> None:
        """Validate that all file IDs exist and belong to the user"""
        for file_id in file_ids:
            file_metadata = self.file_repo.get_file_by_id_and_user(file_id, user_id)
            if file_metadata is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"File with ID '{file_id}' not found"
                )
    
    async def create_task(
        self,
        user_id: str,
        request: CreateTaskRequest,
        api_key: str,
    ) -> Task:
        self._validate_file_ids(user_id, request.file_ids)
        
        task = self.task_repo.create_task(
            task_id=str(uuid4()),
            user_id=user_id,
            prompt=request.prompt,
            created_at=datetime.now(timezone.utc),
            attached_file_ids=request.file_ids,
        )
        
        await self.sse_service.emit_event(
            user_id=user_id,
            event=create_task_created_event(task),
        )
        
        await self.work_queue_service.enqueue(WorkQueueItem.make_task_decomposition_item(task, api_key))
        
        return task
    