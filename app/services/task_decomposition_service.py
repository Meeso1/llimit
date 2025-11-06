from dataclasses import dataclass

from app.services.llm_service_base import LlmService, LlmMessage


@dataclass
class TaskStepDefinition:
    """Definition of a task step returned by decomposition"""
    step_number: int
    prompt: str
    depends_on_steps: list[int]
    additional_context: dict[str, str] | None


@dataclass
class TaskDecompositionResult:
    """Result of task decomposition"""
    title: str
    steps: list[TaskStepDefinition]


# TODO: Complete implementation
class TaskDecompositionService:
    """
    Service responsible for breaking down complex prompts into actionable steps.
    
    This service analyzes the user's prompt and determines:
    - A descriptive title for the task
    - Individual steps needed to complete the task
    - Dependencies between steps
    - Any additional context needed for each step
    """
    
    def __init__(self, llm_service: LlmService) -> None:
        self.llm_service = llm_service
    
    async def decompose_task(
        self,
        user_prompt: str,
        api_key: str,
    ) -> TaskDecompositionResult:
        """
        Decompose a complex task prompt into discrete steps.
        
        Args:
            user_prompt: The original user prompt describing the task
            api_key: API key for LLM service
            
        Returns:
            TaskDecompositionResult with title and list of step definitions
        """
        # TODO: Implement actual decomposition logic
        # For now, return a simple single-step breakdown
        
        # The decomposition should:
        # 1. Analyze the prompt complexity
        # 2. Identify distinct subtasks
        # 3. Determine dependencies (e.g., step 2 needs output from step 1)
        # 4. Generate a title from the prompt
        # 5. Create step prompts that are clear and actionable
        
        # Example implementation structure:
        # system_prompt = self._build_decomposition_system_prompt()
        # messages = [LlmMessage(role="user", content=user_prompt)]
        # 
        # response = await self.llm_service.get_completion(
        #     api_key=api_key,
        #     model="openai/gpt-4o",  # Use a smart model for decomposition
        #     messages=messages,
        #     additional_requested_data={
        #         "title": "A concise title for this task",
        #         "steps": "JSON array of steps with prompts and dependencies"
        #     },
        # )
        
        # For now, simple stub implementation
        return TaskDecompositionResult(
            title=f"Task: {user_prompt[:50]}...",
            steps=[
                TaskStepDefinition(
                    step_number=1,
                    prompt=user_prompt,
                    depends_on_steps=[],
                    additional_context=None,
                )
            ],
        )
    
    def _build_decomposition_system_prompt(self) -> str:
        """Build the system prompt for task decomposition"""
        # TODO: Implement comprehensive system prompt
        return """You are a task decomposition assistant. 
        Break down complex tasks into clear, actionable steps.
        Identify dependencies between steps.
        Generate a concise title for the task."""

