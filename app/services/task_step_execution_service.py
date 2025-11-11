from datetime import datetime, timezone

from app.db.task_repo import TaskRepo
from utils import not_none
from app.events.task_events import create_task_step_completed_event, create_task_completed_event
from app.models.task.enums import TaskStatus, StepStatus, StepType
from app.models.task.models import Task, TaskStep, NormalTaskStep, NormalTaskStepDefinition
from app.models.task.work_queue import WorkQueueItem
from app.services.llm_service_base import LlmService, LlmMessage
from app.services.sse_service import SseService
from app.services.task_model_selection_service import TaskModelSelectionService
from prompts.task_prompts import TASK_STEP_OUTPUT_DESCRIPTION


class TaskStepExecutionError(Exception):
    pass


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
        Should only be called for normal steps.
        """
        step = not_none(self.task_repo.get_step_by_id(step_id), f"Step {step_id}")
        task = not_none(self.task_repo.get_task_by_id(task_id, user_id), f"Task {task_id}")
        
        if step.step_type == StepType.REEVALUATE:
            raise TaskStepExecutionError(
                f"Step {step_id} is a reevaluate step and should not be passed to execute_step. "
                "Reevaluate steps are handled by the decomposition service."
            )
        
        if not isinstance(step, NormalTaskStep):
            raise TaskStepExecutionError(
                f"Step {step_id} is not a normal step (type: {step.step_type})"
            )
        
        # Normal step execution
        if step.model_name is None:
            step_def = NormalTaskStepDefinition(
                prompt=step.prompt,
                step_type=step.step_type,
                complexity=step.complexity,
                required_capabilities=step.required_capabilities,
            )
            model_name = self.model_selection_service.select_model_for_step(step_def)
            
            updated_step = not_none(self.task_repo.update_task_step(
                step_id=step.id,
                model_name=model_name,
            ), f"Step {step.id} after model selection")
            
            if not isinstance(updated_step, NormalTaskStep):
                raise TaskStepExecutionError(
                    f"Step {step_id} changed type after update (expected NormalTaskStep, got {type(updated_step).__name__})"
                )
            
            step = updated_step
                
        self.task_repo.update_task_step(
            step_id=step.id,
            status=StepStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
        )

        all_steps = not_none(
            self.task_repo.get_steps_by_task_id(task.id, task.user_id, exclude_abandoned=True),
            f"Steps for task {task.id}"
        )
        
        context = self._build_step_context(task, step, all_steps)
        
        messages = [LlmMessage(role="user", content=context, additional_data={})]
        
        response = await self.llm_service.get_completion(
            api_key=api_key,
            model=step.model_name or "google/gemini-2.5-flash-lite",
            messages=messages,
            additional_requested_data={
                "output": TASK_STEP_OUTPUT_DESCRIPTION
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
        
        updated_step = not_none(self.task_repo.get_step_by_id(step.id), f"Step {step.id} after update")
        
        await self.sse_service.emit_event(
            user_id=task.user_id,
            event=create_task_step_completed_event(task, updated_step),
        )
        
        next_items, is_done = await self._get_next_work_items_and_check_if_done(task, step, all_steps, api_key)
        if is_done:
            await self._handle_task_completion(task, all_steps)
                
        return next_items
    
    def _build_step_context(self, task: Task, step: TaskStep, all_steps: list[TaskStep]) -> str:
        """Build context for step execution from task and previous steps"""
        context = f"Task: {task.title or task.prompt}\n\n"
        
        completed_steps = [s for s in all_steps if s.status == StepStatus.COMPLETED and s.step_number < step.step_number]
        if completed_steps:
            context += "Previous step results:\n"
            for prev_step in completed_steps:
                context += f"\nStep {prev_step.step_number + 1}: {prev_step.prompt}\n"
                if isinstance(prev_step, NormalTaskStep) and prev_step.output:
                    context += f"Output: {prev_step.output}\n"
        
        context += f"\nCurrent step (Step {step.step_number + 1}):\n{step.prompt}\n"
        
        return context
    
    async def _get_next_work_items_and_check_if_done(
        self,
        task: Task,
        completed_step: TaskStep,
        all_steps: list[TaskStep],
        api_key: str,
    ) -> tuple[list[WorkQueueItem], bool]:
        """Get the next work items to queue after completing a step, returns (work_items, is_done)"""
        next_step_number = completed_step.step_number + 1
        next_steps = [s for s in all_steps if s.step_number == next_step_number]
        
        if next_steps:
            next_step = next_steps[0]
            # Queue different work item types based on step type
            if next_step.step_type == StepType.REEVALUATE:
                return [WorkQueueItem.make_task_reevaluation_item(task, next_step.id, api_key)], False
            else:
                return [WorkQueueItem.make_task_step_execution_item(task, next_step.id, api_key)], False
        else:
            is_done = all(s.status == StepStatus.COMPLETED for s in all_steps)
            return [], is_done
        
    async def _handle_task_completion(self, task: Task, all_steps: list[TaskStep]) -> None:
        # Find the last completed step with output
        completed_steps_with_output = [
            s for s in all_steps 
            if s.status == StepStatus.COMPLETED and isinstance(s, NormalTaskStep) and s.output
        ]
        
        if not completed_steps_with_output:
            raise TaskStepExecutionError(
                f"Task {task.id} has no completed steps with output. Cannot complete task."
            )
        
        final_output = completed_steps_with_output[-1].output
        
        updated_task = not_none(self.task_repo.update_task_final_status(
            task_id=task.id,
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            output=final_output,
        ), f"Task {task.id} after completion")
        
        await self.sse_service.emit_event(
            user_id=task.user_id,
            event=create_task_completed_event(updated_task),
        )
