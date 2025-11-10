import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from app.db.task_repo import TaskRepo
from app.events.task_events import (
    create_task_steps_generated_event,
    create_task_step_completed_event,
    create_task_completed_event,
    create_task_failed_event,
)
from app.models.task.enums import TaskStatus
from app.models.task.models import Task, TaskStep
from app.models.task.requests import CreateTaskRequest
from app.services.llm_service_base import LlmService
from app.services.sse_service import SseService
from app.services.task_decomposition_service import TaskDecompositionService
from app.services.task_model_selection_service import TaskModelSelectionService


# TODO: Complete implementation of step execution
class TaskService:
    def __init__(
        self,
        task_repo: TaskRepo,
        llm_service: LlmService,
        sse_service: SseService,
        decomposition_service: TaskDecompositionService,
        model_selection_service: TaskModelSelectionService,
    ) -> None:
        self.task_repo = task_repo
        self.llm_service = llm_service
        self.sse_service = sse_service
        self.decomposition_service = decomposition_service
        self.model_selection_service = model_selection_service
    
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
        
        asyncio.create_task(self._process_task(task, api_key))
        
        return task
    
    async def _process_task(self, task: Task, api_key: str) -> None:
        try:
            task, steps = await self._decompose_task(task, api_key)
            
            # Step 2: Execute steps (TODO: implement full execution logic)
            # For now, this is a placeholder
            # The actual implementation should:
            # - Execute steps respecting dependencies
            # - Select appropriate models for each step
            # - Pass outputs from completed steps to dependent steps
            # - Emit events for each completed step
            
            updated_task = self.task_repo.update_task_final_status(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
            )
            
            if not updated_task:
                raise Exception("Task was not found in database when setting completion status")

            await self.sse_service.emit_event(
                user_id=task.user_id,
                event=create_task_completed_event(updated_task),
            )
            
        except Exception as e:
            self.task_repo.update_task_final_status(
                task_id=task.id,
                status=TaskStatus.FAILED,
                completed_at=datetime.now(timezone.utc),
            )
            
            await self.sse_service.emit_event(
                user_id=task.user_id,
                event=create_task_failed_event(task, str(e)),
            )

    async def _decompose_task(self, task: Task, api_key: str) -> tuple[Task, list[TaskStep]]:
        decomposition = await self.decomposition_service.decompose_task(
            user_prompt=task.prompt,
            api_key=api_key,
        )
        
        task = self._expect_not_none(self.task_repo.update_task_after_steps_generation(
            task_id=task.id,
            title=decomposition.title,
            steps=decomposition.steps,
        ))
        
        steps = self._expect_not_none(self.task_repo.get_steps_by_task_id(task.id, task.user_id))
        
        await self.sse_service.emit_event(
            user_id=task.user_id,
            event=create_task_steps_generated_event(task, steps),
        )
        
        return task, steps
    
    def _expect_not_none[T](self, value: T | None, value_name: str | None = None) -> T:
        if value is None:
            raise Exception(f"{value_name} is None, which is unexpected")
        return value
    