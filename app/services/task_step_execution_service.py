from datetime import datetime, timezone

from app.db.task_repo import TaskRepo
from app.events.task_events import create_task_step_completed_event, create_task_completed_event
from app.models.task.enums import TaskStatus, StepStatus
from app.models.task.models import Task, TaskStep, TaskStepDefinition
from app.models.task.work_queue import WorkQueueItem, WorkItemType
from app.services.llm_service_base import LlmService, LlmMessage
from app.services.sse_service import SseService
from app.services.task_model_selection_service import TaskModelSelectionService


class TaskStepExecutionService:
    """Service to execute individual task steps"""
    
    def __init__(
        self,
        task_repo: TaskRepo,
        llm_service: LlmService,
        sse_service: SseService,
        model_selection_service: TaskModelSelectionService,
    ) -> None:
        self.task_repo = task_repo
        self.llm_service = llm_service
        self.sse_service = sse_service
        self.model_selection_service = model_selection_service
    
    async def execute_step(
        self,
        step_id: str,
        task_id: str,
        user_id: str,
        api_key: str,
    ) -> list[WorkQueueItem]:
        """
        Execute a task step and return next work items to queue.
        """
        step = self.task_repo.get_step_by_id(step_id)
        if not step:
            raise Exception(f"Step {step_id} not found")
        
        task = self.task_repo.get_task_by_id(task_id, user_id)
        if not task:
            raise Exception(f"Task {task_id} not found")
        
        if step.model_name is None:
            step_def = TaskStepDefinition(
                prompt=step.prompt,
                complexity=step.complexity,
                required_capabilities=step.required_capabilities,
            )
            model_name = self.model_selection_service.select_model_for_step(step_def)
            
            updated_step = self.task_repo.update_task_step(
                step_id=step.id,
                model_name=model_name,
            )
            if updated_step:
                step = updated_step
                
        self.task_repo.update_task_step(
            step_id=step.id,
            status=StepStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
        )
        
        context = self._build_step_context(task, step)
        
        messages = [LlmMessage(role="user", content=context)]
        
        response = await self.llm_service.get_completion(
            api_key=api_key,
            model=step.model_name or "google/gemini-2.5-flash-lite",
            messages=messages,
            additional_requested_data={
                "output": "Concise result of this step that can be used by subsequent steps. Include only the essential information."
            },
            temperature=0.7,
        )
        
        output = response.additional_data.get("output", "")
        
        self.task_repo.update_task_step(
            step_id=step.id,
            status=StepStatus.COMPLETED,
            response_content=response.content,
            output=output,
            completed_at=datetime.now(timezone.utc),
        )
        
        updated_step = self.task_repo.get_step_by_id(step.id)
        if updated_step:
            await self.sse_service.emit_event(
                user_id=task.user_id,
                event=create_task_step_completed_event(task, updated_step),
            )
        
        next_items, is_done = await self._get_next_work_items_and_check_if_done(task, step, api_key)
        if is_done:
            await self._handle_task_completion(task)
                
        return next_items
    
    def _build_step_context(self, task: Task, step: TaskStep) -> str:
        """Build context for step execution from task and previous steps"""
        all_steps = self.task_repo.get_steps_by_task_id(task.id, task.user_id)
        if not all_steps:
            all_steps = []
        
        context = f"Task: {task.title or task.prompt}\n\n"
        
        completed_steps = [s for s in all_steps if s.status == StepStatus.COMPLETED and s.step_number < step.step_number]
        if completed_steps:
            context += "Previous step results:\n"
            for prev_step in completed_steps:
                context += f"\nStep {prev_step.step_number + 1}: {prev_step.prompt}\n"
                if prev_step.output:
                    context += f"Output: {prev_step.output}\n"
        
        context += f"\nCurrent step (Step {step.step_number + 1}):\n{step.prompt}\n"
        
        return context
    
    async def _get_next_work_items_and_check_if_done(
        self,
        task: Task,
        completed_step: TaskStep,
        api_key: str,
    ) -> tuple[list[WorkQueueItem], bool]:
        """Get the next work items to queue after completing a step"""
        all_steps = self.task_repo.get_steps_by_task_id(task.id, task.user_id)
        if all_steps is None:
            return [], False
        
        next_step_number = completed_step.step_number + 1
        next_steps = [s for s in all_steps if s.step_number == next_step_number]
        
        if next_steps:
            return [WorkQueueItem.make_task_step_execution_item(task, next_steps[0].id, api_key)]
        else:
            return [], all(s.status == StepStatus.COMPLETED for s in all_steps)
        
    async def _handle_task_completion(self, task: Task) -> None:
        updated_task = self.task_repo.update_task_final_status(
            task_id=task.id,
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        
        if updated_task:
            await self.sse_service.emit_event(
                user_id=task.user_id,
                event=create_task_completed_event(updated_task),
            )
