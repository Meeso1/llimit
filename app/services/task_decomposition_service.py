import json
from uuid import uuid4

from app.db.task_repo import TaskRepo
from app.events.task_events import create_task_steps_generated_event
from app.services.llm_service_base import LlmService, LlmMessage
from app.services.sse_service import SseService
from app.models.task.models import TaskDecompositionResult, TaskStepDefinition
from app.models.task.work_queue import WorkQueueItem, WorkItemType
from app.models.task.enums import ComplexityLevel, ModelCapability


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
        task = self.task_repo.get_task_by_id(task_id, user_id)
        if not task:
            raise Exception(f"Task {task_id} not found")
        
        decomposition = await self.decompose_task(task.prompt, api_key)
        
        updated_task = self.task_repo.update_task_after_steps_generation(
            task_id=task.id,
            title=decomposition.title,
            steps=decomposition.steps,
        )
        
        if not updated_task:
            raise Exception("Failed to update task after decomposition")
        
        steps = self.task_repo.get_steps_by_task_id(task.id, user_id)
        if not steps:
            raise Exception("Failed to retrieve generated steps")
        
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
                "title": "A concise title (3-8 words) that summarizes the task",
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
        
        content = f"""You are a task decomposition assistant. Your goal is to break down complex user tasks into a series of sequential steps that can be executed independently by different AI models.

When decomposing a task, follow these guidelines:
1. Break the task into clear, sequential steps
2. Each step should be self-contained and actionable
3. For each step, specify:
   - A clear prompt that describes what needs to be done
   - The complexity level: {complexity_levels}
   - Required model capabilities (only specify if actually needed): {capabilities}

Important notes about step execution:
- When a step is executed, all previous steps' prompts and outputs will be automatically provided to the model
- Steps can naturally reference previous steps (e.g., "use the information from step 3", "based on the previous analysis")
- Later steps can build upon earlier outputs without special syntax

Simple tasks:
- If the task is simple and doesn't require multiple steps, return a single step representing the entire task
- The prompt can either be the same as the user's request, or rephrased to be clearer and more actionable for an LLM

Example (multi-step):
If I ask to "research the population of France and then create a comparison chart with Germany":
- Step 1: "Find the current population of France" (complexity: low, capabilities: [web_search])
- Step 2: "Find the current population of Germany" (complexity: low, capabilities: [web_search])
- Step 3: "Create a comparison chart showing the populations of France and Germany based on the previous findings" (complexity: medium, capabilities: [])

Example (simple task):
If I ask to "write a poem about cats":
- Step 1: "Write a creative and engaging poem about cats" (complexity: low, capabilities: [])

Now, please decompose this task:
{user_prompt}"""
        
        return [LlmMessage(role="user", content=content, additional_data={})]

    def _build_steps_description(self) -> str:
        complexity_levels = ", ".join([f'"{level.value}"' for level in ComplexityLevel])
        capabilities = ", ".join([f'"{cap.value}"' for cap in ModelCapability])
        
        return f"""JSON array of step objects. Each object must have:
- "prompt": string describing the step task (can reference previous steps naturally, e.g. "analyze the results from step 2")
- "complexity": string, one of: {complexity_levels}
- "required_capabilities": array of strings from: {capabilities} (only include capabilities that are actually needed; can be empty array if no special capabilities required)

Example: [{{"prompt": "Research X", "complexity": "low", "required_capabilities": ["web_search"]}}, {{"prompt": "Analyze the research findings", "complexity": "medium", "required_capabilities": []}}]"""
