import json

from app.db.task_repo import TaskRepo
from utils import not_none
from app.events.task_events import create_task_steps_generated_event
from app.services.llm_service_base import LlmService, LlmMessage
from app.services.sse_service import SseService
from app.models.task.models import TaskDecompositionResult, TaskStepDefinition
from app.models.task.work_queue import WorkQueueItem, WorkItemType
from app.models.task.enums import ComplexityLevel, ModelCapability
from prompts.task_prompts import (
    TASK_DECOMPOSITION_PROMPT_TEMPLATE,
    TASK_TITLE_DESCRIPTION,
    TASK_STEPS_DESCRIPTION_TEMPLATE,
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
        
        try:
            steps_data = json.loads(steps_json)
        except json.JSONDecodeError as e:
            raise TaskDecompositionError(f"Failed to parse steps JSON: {e}")
        
        if not isinstance(steps_data, list) or len(steps_data) == 0:
            raise TaskDecompositionError("Steps array is empty or invalid")
        
        steps = []
        for i, step_data in enumerate(steps_data):
            if not isinstance(step_data, dict):
                raise TaskDecompositionError(f"Step {i+1} is not a valid object")
            
            prompt = step_data.get("prompt", "").strip()
            if not prompt:
                raise TaskDecompositionError(f"Step {i+1} is missing a prompt")
            
            try:
                complexity_str = step_data.get("complexity", "").lower()
                if not complexity_str:
                    raise TaskDecompositionError(f"Step {i+1} is missing complexity level")
                complexity = ComplexityLevel(complexity_str)
            except ValueError:
                raise TaskDecompositionError(f"Step {i+1} has invalid complexity: {complexity_str}")
            
            capabilities_list = step_data.get("required_capabilities", [])
            if not isinstance(capabilities_list, list):
                raise TaskDecompositionError(f"Step {i+1} has invalid required_capabilities format")
            
            capabilities = []
            for cap_str in capabilities_list:
                try:
                    capabilities.append(ModelCapability(cap_str.lower()))
                except ValueError:
                    raise TaskDecompositionError(f"Step {i+1} has invalid capability: {cap_str}")
            
            steps.append(TaskStepDefinition(
                prompt=prompt,
                complexity=complexity,
                required_capabilities=capabilities,
            ))
        
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
