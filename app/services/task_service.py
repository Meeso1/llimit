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
from app.models.task.enums import TaskStatus, StepStatus
from app.models.task.models import Task, TaskStep
from app.models.task.requests import CreateTaskRequest
from app.services.llm_service_base import LlmService, LlmMessage
from app.services.sse_service import SseService
from app.services.task_decomposition_service import TaskDecompositionService
from app.services.task_model_selection_service import TaskModelSelectionService


# TODO: Complete implementation of step execution
class TaskService:
    """
    Main service for managing multi-step tasks.
    
    Coordinates:
    - Task creation and decomposition
    - Model selection for each step
    - Step execution with dependency management
    - SSE event emission for progress updates
    """
    
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
        """
        Create a new task and start processing it asynchronously.
        
        Args:
            user_id: ID of the user creating the task
            request: Task creation request with prompt
            api_key: API key for LLM calls
            
        Returns:
            Created Task object (decomposition happens asynchronously)
        """
        task_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        # Create initial task
        task = self.task_repo.create_task(
            task_id=task_id,
            user_id=user_id,
            prompt=request.prompt,
            created_at=now,
        )
        
        # Start decomposition and execution in background
        asyncio.create_task(self._process_task(task, api_key))
        
        return task
    
    async def _process_task(self, task: Task, api_key: str) -> None:
        """
        Background task to decompose and execute a task.
        
        Args:
            task: The task to process
            api_key: API key for LLM calls
        """
        try:
            # Step 1: Decompose the task into steps
            decomposition = await self.decomposition_service.decompose_task(
                user_prompt=task.prompt,
                api_key=api_key,
            )
            
            # Update task with title and status
            task = self.task_repo.update_task(
                task_id=task.id,
                title=decomposition.title,
                status=TaskStatus.IN_PROGRESS,
                steps_generated=True,
            )
            
            # Create step records in database
            steps: list[TaskStep] = []
            for step_def in decomposition.steps:
                step_id = str(uuid4())
                step = self.task_repo.create_task_step(
                    step_id=step_id,
                    task_id=task.id,
                    step_number=step_def.step_number,
                    prompt=step_def.prompt,
                    depends_on_steps=step_def.depends_on_steps,
                    additional_context=step_def.additional_context,
                )
                steps.append(step)
            
            # Reload task to get updated state
            task = self.task_repo.get_task_by_id(task.id, task.user_id)
            
            # Emit SSE event for steps generated
            await self.sse_service.emit_event(
                user_id=task.user_id,
                event=create_task_steps_generated_event(task, steps),
            )
            
            # Step 2: Execute steps (TODO: implement full execution logic)
            # For now, this is a placeholder
            # The actual implementation should:
            # - Execute steps respecting dependencies
            # - Select appropriate models for each step
            # - Pass outputs from completed steps to dependent steps
            # - Emit events for each completed step
            
            # Mark task as completed
            now = datetime.now(timezone.utc)
            updated_task = self.task_repo.update_task(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                completed_at=now,
            )
            
            # Emit task completed event
            if not updated_task:
                raise Exception("Task was not found in database when setting completion status")

            await self.sse_service.emit_event(
                user_id=task.user_id,
                event=create_task_completed_event(updated_task),
            )
            
        except Exception as e:
            self.task_repo.update_task(
                task_id=task.id,
                status=TaskStatus.FAILED,
            )
            
            await self.sse_service.emit_event(
                user_id=task.user_id,
                event=create_task_failed_event(task, str(e)),
            )
    
    async def _execute_step(
        self,
        step: TaskStep,
        previous_steps: list[TaskStep],
        api_key: str,
    ) -> TaskStep:
        """
        Execute a single task step.
        
        Args:
            step: The step to execute
            previous_steps: List of completed steps (for context)
            api_key: API key for LLM calls
            
        Returns:
            Updated TaskStep with results
        """
        # TODO: Implement step execution with actual LLM calls
        # This should:
        # 1. Select model using model_selection_service
        # 2. Build context from dependent steps
        # 3. Call LLM with appropriate prompt
        # 4. Store results
        # 5. Emit SSE event for completion
        
        now = datetime.now(timezone.utc)
        
        # Update step as in progress
        updated_step = self.task_repo.update_task_step(
            step_id=step.id,
            status=StepStatus.IN_PROGRESS,
            started_at=now,
        )
        
        if not updated_step:
            raise Exception(f"Step {step.id} was not found in database when updating to in_progress")
        
        step = updated_step
        
        # Select model for this step
        model = self.model_selection_service.select_model_for_step(step.prompt)
        
        # Build messages with context from previous steps
        messages = self._build_step_messages(step, previous_steps)
        
        # TODO: Call actual LLM
        # response = await self.llm_service.get_completion(
        #     api_key=api_key,
        #     model=model,
        #     messages=messages,
        # )
        
        # Temporary hardcoded response for testing
        context_summary = ""
        if previous_steps:
            context_summary = f" (building on {len(previous_steps)} previous step(s))"
        
        hardcoded_response = f"Completed: {step.prompt}{context_summary}\n\nThis is a placeholder response generated by the system. Selected model: {model}"
        
        # Update step with results
        completed_at = datetime.now(timezone.utc)
        updated_step = self.task_repo.update_task_step(
            step_id=step.id,
            status=StepStatus.COMPLETED,
            model_name=model,
            response_content=hardcoded_response,
            completed_at=completed_at,
        )
        
        if not updated_step:
            raise Exception(f"Step {step.id} was not found in database when updating to completed")
        
        return updated_step
    
    def _build_step_messages(
        self,
        step: TaskStep,
        previous_steps: list[TaskStep],
    ) -> list[LlmMessage]:
        """
        Build LLM messages for a step, including context from previous steps.
        
        Args:
            step: The current step to execute
            previous_steps: List of completed steps
            
        Returns:
            List of LLM messages
        """
        messages: list[LlmMessage] = []
        
        # Add context from dependent steps
        if step.depends_on_steps:
            for prev_step in previous_steps:
                if prev_step.step_number in step.depends_on_steps:
                    messages.append(LlmMessage(
                        role="user",
                        content=f"[Previous step {prev_step.step_number}] {prev_step.prompt}",
                    ))
                    if prev_step.response_content:
                        messages.append(LlmMessage(
                            role="assistant",
                            content=prev_step.response_content,
                        ))
        
        # Add current step prompt
        messages.append(LlmMessage(
            role="user",
            content=step.prompt,
        ))
        
        return messages

