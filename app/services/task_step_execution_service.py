from datetime import datetime, timezone

from app.db.task_repo import TaskRepo
from app.services.llm_logging_service import LlmLoggingService
from utils import not_none
from app.events.task_events import create_task_step_completed_event, create_task_completed_event
from app.models.task.enums import TaskStatus, StepStatus, StepType, ModelCapability
from app.models.task.models import Task, TaskStep, NormalTaskStep, NormalTaskStepDefinition
from app.models.task.work_queue import WorkQueueItem
from app.services.llm.config.llm_config import LlmConfig
from app.services.llm.config.reasoning_config import ReasoningConfig
from app.services.llm.config.web_search_config import WebSearchConfig, SearchContextSize
from app.services.llm.llm_service_base import LlmService, LlmMessage
from app.services.sse_service import SseService
from app.services.task_model_selection_service import TaskModelSelectionService
from prompts.task_prompts import TASK_STEP_OUTPUT_DESCRIPTION, TASK_STEP_FAILURE_REASON_DESCRIPTION


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
        llm_logging_service: LlmLoggingService,
    ) -> None:
        self.task_repo = task_repo
        self.llm_service = llm_service
        self.sse_service = sse_service
        self.model_selection_service = model_selection_service
        self.llm_logging_service = llm_logging_service
    
    def _ensure_step_is_normal(self, step: TaskStep) -> NormalTaskStep:
        """Ensure the step is a normal step, raise error otherwise"""
        if step.step_type == StepType.REEVALUATE:
            raise TaskStepExecutionError(
                f"Step {step.id} is a reevaluate step and should not be passed to execute_step. "
                "Reevaluate steps are handled by the decomposition service."
            )
        
        if not isinstance(step, NormalTaskStep):
            raise TaskStepExecutionError(
                f"Step {step.id} is not a normal step (type: {step.step_type})"
            )
        
        return step

    def _build_web_search_config(self, step: NormalTaskStep) -> WebSearchConfig:
        """Build web search configuration based on step's required capabilities"""
        has_exa = ModelCapability.EXA_SEARCH in step.required_capabilities
        has_native = ModelCapability.NATIVE_WEB_SEARCH in step.required_capabilities
        
        if not has_exa and not has_native:
            return WebSearchConfig.default()
        
        return WebSearchConfig(
            use_exa_search=has_exa,
            use_native_search=has_native,
            max_results=5,
            search_context_size=SearchContextSize.MEDIUM,
        )

    def _build_reasoning_config(self, step: NormalTaskStep) -> ReasoningConfig:
        """Build reasoning configuration based on step's required capabilities"""
        has_reasoning = ModelCapability.REASONING in step.required_capabilities
        
        if not has_reasoning:
            return ReasoningConfig.default()
        
        return ReasoningConfig.with_medium_effort()

    def _build_llm_config(self, step: NormalTaskStep) -> LlmConfig:
        """Build LLM configuration based on step's required capabilities"""
        return LlmConfig(
            web_search=self._build_web_search_config(step),
            reasoning=self._build_reasoning_config(step),
        )
    
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
        step = self._ensure_step_is_normal(step)
        
        task = not_none(self.task_repo.get_task_by_id(task_id, user_id), f"Task {task_id}")
        
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
        
        messages = [LlmMessage.user(self._build_step_context(task, step, all_steps))]
        config = self._build_llm_config(step)
        logger = self.llm_logging_service.create_for_task(task.id)
        
        response = await self.llm_service.get_completion(
            api_key=api_key,
            model=step.model_name or "google/gemini-2.5-flash-lite",
            messages=messages,
            additional_requested_data={
                "output": TASK_STEP_OUTPUT_DESCRIPTION,
                "failure_reason": TASK_STEP_FAILURE_REASON_DESCRIPTION,
            },
            temperature=0.7,
            config=config,
            logger=logger,
        )
        
        output = response.additional_data.get("output", "")
        failure_reason = response.additional_data.get("failure_reason", "").strip()
        
        # Determine status based on whether the step failed
        if failure_reason:
            status = StepStatus.COULD_NOT_COMPLETE
        else:
            status = StepStatus.COMPLETED
        
        self.task_repo.update_task_step(
            step_id=step.id,
            status=status,
            response_content=response.content,
            output=output,
            failure_reason=failure_reason if failure_reason else None,
            completed_at=datetime.now(timezone.utc),
        )
        
        updated_step = not_none(self.task_repo.get_step_by_id(step.id), f"Step {step.id} after update")
        
        await self.sse_service.emit_event(
            user_id=task.user_id,
            event=create_task_step_completed_event(task, updated_step),
        )
        
        # If step failed, create a reevaluation step
        if failure_reason:
            return await self._handle_step_failure(task, updated_step, failure_reason, api_key)
        
        # Otherwise, proceed normally
        updated_all_steps = not_none(
            self.task_repo.get_steps_by_task_id(task.id, task.user_id, exclude_abandoned=True),
            f"Steps for task {task.id}"
        )
        next_items, is_done = await self._get_next_work_items_and_check_if_done(task, step, updated_all_steps, api_key)
        if is_done:
            await self._handle_task_completion(task, updated_all_steps)
                
        return next_items
    
    async def _handle_step_failure(
        self,
        task: Task,
        failed_step: TaskStep,
        failure_reason: str,
        api_key: str,
    ) -> list[WorkQueueItem]:
        """Handle a step failure by creating a reevaluation step"""
        reevaluation_step = self.task_repo.create_reevaluation_step(
            task_id=task.id,
            step_number=failed_step.step_number,
            prompt=failure_reason,
            is_planned=False,
        )
        
        return [WorkQueueItem.make_task_reevaluation_item(task, reevaluation_step.id, api_key)]
    
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
