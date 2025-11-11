import json
from datetime import datetime, timezone

from app.db.task_repo import TaskRepo
from utils import not_none
from app.events.task_events import create_task_step_completed_event, create_task_steps_generated_event, create_task_steps_regenerated_event
from app.services.llm_service_base import LlmService, LlmMessage
from app.services.sse_service import SseService
from app.models.task.models import (
    TaskDecompositionResult,
    TaskStepDefinition,
    NormalTaskStepDefinition,
    ReevaluateTaskStepDefinition,
    Task,
    TaskStep,
)
from app.models.task.work_queue import WorkQueueItem
from app.models.task.enums import ComplexityLevel, ModelCapability, StepStatus, StepType
from prompts.task_prompts import (
    TASK_DECOMPOSITION_PROMPT_TEMPLATE,
    TASK_TITLE_DESCRIPTION,
    TASK_STEPS_DESCRIPTION_TEMPLATE,
    TASK_REEVALUATION_PROMPT_TEMPLATE,
    TASK_REEVALUATION_STEPS_DESCRIPTION_TEMPLATE,
    TASK_PREVIOUS_STEP_FORMAT,
    TASK_REEVALUATE_STEP_FORMAT,
)


class TaskDecompositionError(Exception):
    pass


class TaskDecompositionService:
    def __init__(
        self,
        llm_service: LlmService,
        task_repo: TaskRepo,
        sse_service: SseService,
    ) -> None:
        self.llm_service = llm_service
        self.task_repo = task_repo
        self.sse_service = sse_service
    
    async def decompose_and_queue_task(
        self,
        task_id: str,
        user_id: str,
        api_key: str,
    ) -> list[WorkQueueItem]:
        """
        Decompose a task, update DB, emit events, and return next work items to queue.
        """
        task = not_none(self.task_repo.get_task_by_id(task_id, user_id), f"Task {task_id}")
        
        decomposition = await self.decompose_task(task.prompt, api_key)
        
        updated_task = not_none(
            self.task_repo.update_task_after_steps_generation(
                task_id=task.id,
                title=decomposition.title,
                steps=decomposition.steps,
            ),
            f"Task {task.id} after decomposition"
        )
        
        steps = not_none(self.task_repo.get_steps_by_task_id(task.id, user_id), f"Generated steps for task {task.id}")
        
        await self.sse_service.emit_event(
            user_id=user_id,
            event=create_task_steps_generated_event(updated_task, steps),
        )
        
        if len(steps) > 0:
            return [WorkQueueItem.make_task_step_execution_item(task, steps[0].id, api_key)]
        
        return []
    
    async def reevaluate_and_queue_task(
        self,
        step_id: str,
        task_id: str,
        user_id: str,
        api_key: str,
    ) -> list[WorkQueueItem]:
        """
        Reevaluate a task after a reevaluate step, update DB, emit events, and return next work items to queue.
        """
        task = not_none(self.task_repo.get_task_by_id(task_id, user_id), f"Task {task_id}")
        reevaluate_step = not_none(self.task_repo.get_step_by_id(step_id), f"Step {step_id}")
        
        if reevaluate_step.step_type != StepType.REEVALUATE:
            raise TaskDecompositionError(
                f"Step {step_id} is not a reevaluate step (type: {reevaluate_step.step_type})"
            )
        
        all_steps = not_none(
            self.task_repo.get_steps_by_task_id(task.id, user_id, exclude_abandoned=True),
            f"Steps for task {task.id}"
        )
        
        steps_before = [s for s in all_steps if s.step_number < reevaluate_step.step_number]
        incomplete_steps = [s for s in steps_before if s.status != StepStatus.COMPLETED]
        if incomplete_steps:
            raise TaskDecompositionError(
                f"Cannot reevaluate: {len(incomplete_steps)} step(s) before reevaluation are not completed"
            )
        
        completed_steps_before = steps_before
        
        self.task_repo.update_task_step(
            step_id=reevaluate_step.id,
            status=StepStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
        )
        
        new_steps_defs = await self.reevaluate_task(
            task=task,
            reevaluate_step=reevaluate_step,
            previous_steps=completed_steps_before,
            api_key=api_key,
        )
        
        self.task_repo.update_task_step(
            step_id=reevaluate_step.id,
            status=StepStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        
        updated_reevaluate_step = not_none(
            self.task_repo.get_step_by_id(reevaluate_step.id),
            f"Reevaluate step {reevaluate_step.id} after completion"
        )
        
        await self.sse_service.emit_event(
            user_id=user_id,
            event=create_task_step_completed_event(task, updated_reevaluate_step),
        )
        
        self.task_repo.mark_steps_as_abandoned_after(task.id, reevaluate_step.step_number)
        
        new_steps = self.task_repo.insert_new_steps_after_reevaluation(
            task_id=task.id,
            after_step_number=reevaluate_step.step_number,
            new_steps=new_steps_defs,
        )
        
        await self.sse_service.emit_event(
            user_id=user_id,
            event=create_task_steps_regenerated_event(task, new_steps),
        )
        
        if len(new_steps) > 0:
            return [WorkQueueItem.make_task_step_execution_item(task, new_steps[0].id, api_key)]
        
        return []
    
    async def decompose_task(
        self,
        user_prompt: str,
        api_key: str,
    ) -> TaskDecompositionResult:
        """Decomposes a user task into a structured sequence of steps."""
        response = await self.llm_service.get_completion(
            api_key=api_key,
            model="google/gemini-2.5-pro",
            messages=self._build_messages(user_prompt),
            additional_requested_data={
                "title": TASK_TITLE_DESCRIPTION,
                "steps": self._build_steps_description(),
            },
            temperature=0.7,
        )
        
        return self._parse_response(response)
    
    def _parse_response(self, response: LlmMessage) -> TaskDecompositionResult:
        title = response.additional_data.get("title", "[Untitled]").strip()
        
        steps_json = response.additional_data.get("steps", "")
        if not steps_json:
            raise TaskDecompositionError("Steps data is missing")
        
        steps = self._parse_steps_json(steps_json, "Step")
        
        return TaskDecompositionResult(title=title, steps=steps)

    def _build_messages(self, user_prompt: str) -> list[LlmMessage]:
        complexity_levels = ", ".join([f'"{level.value}"' for level in ComplexityLevel])
        capabilities = ", ".join([f'"{cap.value}"' for cap in ModelCapability])
        
        content = TASK_DECOMPOSITION_PROMPT_TEMPLATE.format(
            complexity_levels=complexity_levels,
            capabilities=capabilities,
            user_prompt=user_prompt,
        )
        
        return [LlmMessage(role="user", content=content, additional_data={})]

    def _build_steps_description(self) -> str:
        complexity_levels = ", ".join([f'"{level.value}"' for level in ComplexityLevel])
        capabilities = ", ".join([f'"{cap.value}"' for cap in ModelCapability])
        
        return TASK_STEPS_DESCRIPTION_TEMPLATE.format(
            complexity_levels=complexity_levels,
            capabilities=capabilities,
        )
    
    async def reevaluate_task(
        self,
        task: Task,
        reevaluate_step: TaskStep,
        previous_steps: list[TaskStep],
        api_key: str,
    ) -> list[TaskStepDefinition]:
        """Reevaluate a task based on previous steps and generate new steps"""
        response = await self.llm_service.get_completion(
            api_key=api_key,
            model="google/gemini-2.5-pro",
            messages=self._build_reevaluation_messages(task, reevaluate_step, previous_steps),
            additional_requested_data={
                "steps": self._build_reevaluation_steps_description(),
            },
            temperature=0.7,
        )
        
        return self._parse_reevaluation_response(response)
    
    def _build_reevaluation_messages(
        self, 
        task: Task, 
        reevaluate_step: TaskStep,
        previous_steps: list[TaskStep]
    ) -> list[LlmMessage]:
        complexity_levels = ", ".join([f'"{level.value}"' for level in ComplexityLevel])
        capabilities = ", ".join([f'"{cap.value}"' for cap in ModelCapability])
        
        # Build previous steps context
        previous_steps_text = ""
        if previous_steps:
            previous_steps_text = "Previous steps and their results:\n"
            for step in previous_steps:
                previous_steps_text += TASK_PREVIOUS_STEP_FORMAT.format(
                    step_number=step.step_number + 1,
                    step_prompt=step.prompt,
                    step_output=step.output or "(no output)",
                )
        
        # Add reevaluation step
        previous_steps_text += "\n" + TASK_REEVALUATE_STEP_FORMAT.format(
            step_number=reevaluate_step.step_number + 1,
            step_prompt=reevaluate_step.prompt,
        )
        
        content = TASK_REEVALUATION_PROMPT_TEMPLATE.format(
            original_prompt=task.prompt,
            task_title=task.title or "[No title]",
            previous_steps=previous_steps_text,
            complexity_levels=complexity_levels,
            capabilities=capabilities,
        )
        
        return [LlmMessage(role="user", content=content, additional_data={})]
    
    def _build_reevaluation_steps_description(self) -> str:
        complexity_levels = ", ".join([f'"{level.value}"' for level in ComplexityLevel])
        capabilities = ", ".join([f'"{cap.value}"' for cap in ModelCapability])
        
        return TASK_REEVALUATION_STEPS_DESCRIPTION_TEMPLATE.format(
            complexity_levels=complexity_levels,
            capabilities=capabilities,
        )
    
    def _parse_reevaluation_response(self, response: LlmMessage) -> list[TaskStepDefinition]:
        """Parse reevaluation response - uses shared step parsing logic"""
        steps_json = response.additional_data.get("steps", "")
        if not steps_json:
            raise TaskDecompositionError("Steps data is missing from reevaluation")
        
        return self._parse_steps_json(steps_json, "Reevaluation step")
    
    def _parse_steps_json(self, steps_json: str, step_label_prefix: str) -> list[TaskStepDefinition]:
        """Shared logic to parse steps JSON into TaskStepDefinition objects"""
        try:
            steps_data = json.loads(steps_json)
        except json.JSONDecodeError as e:
            raise TaskDecompositionError(f"Failed to parse steps JSON: {e}")
        
        if not isinstance(steps_data, list):
            raise TaskDecompositionError("Steps array is not a list")
        
        steps = []
        for i, step_data in enumerate(steps_data):
            step_label = f"{step_label_prefix} {i+1}"
            
            if not isinstance(step_data, dict):
                raise TaskDecompositionError(f"{step_label} is not a valid object")
            
            prompt = step_data.get("prompt", "").strip()
            if not prompt:
                raise TaskDecompositionError(f"{step_label} is missing a prompt")
            
            try:
                step_type_str = step_data.get("step_type", "normal").lower()
                step_type = StepType(step_type_str)
            except ValueError:
                raise TaskDecompositionError(f"{step_label} has invalid step_type: {step_type_str}")
            
            if step_type == StepType.NORMAL:
                try:
                    complexity_str = step_data.get("complexity", "").lower()
                    if not complexity_str:
                        raise TaskDecompositionError(f"{step_label} is missing complexity level")
                    complexity = ComplexityLevel(complexity_str)
                except ValueError:
                    raise TaskDecompositionError(f"{step_label} has invalid complexity: {complexity_str}")
                
                capabilities_list = step_data.get("required_capabilities", [])
                if not isinstance(capabilities_list, list):
                    raise TaskDecompositionError(f"{step_label} has invalid required_capabilities format")
                
                capabilities = []
                for cap_str in capabilities_list:
                    try:
                        capabilities.append(ModelCapability(cap_str.lower()))
                    except ValueError:
                        raise TaskDecompositionError(f"{step_label} has invalid capability: {cap_str}")
                
                steps.append(NormalTaskStepDefinition(
                    prompt=prompt,
                    step_type=step_type,
                    complexity=complexity,
                    required_capabilities=capabilities,
                ))
            elif step_type == StepType.REEVALUATE:
                steps.append(ReevaluateTaskStepDefinition(
                    prompt=prompt,
                    step_type=step_type,
                ))
            else:
                raise TaskDecompositionError(f"{step_label} has unknown step_type: {step_type}")
        
        return steps
