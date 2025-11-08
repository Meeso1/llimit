from app.services.llm_service_base import LlmService
from app.models.task.models import TaskDecompositionResult, TaskStepDefinition


# TODO: Complete implementation
class TaskDecompositionService:
    def __init__(self, llm_service: LlmService) -> None:
        self.llm_service = llm_service
    
    async def decompose_task(
        self,
        user_prompt: str,
        api_key: str,
    ) -> TaskDecompositionResult:
        # TODO: Implement actual decomposition logic
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
        
        # Temporary hardcoded implementation for testing
        title = user_prompt[:50] + ("..." if len(user_prompt) > 50 else "")
        
        return TaskDecompositionResult(
            title=title,
            steps=[
                TaskStepDefinition(
                    prompt=f"Step 1: Analyze the following request: {user_prompt}",
                ),
                TaskStepDefinition(
                    prompt=f"Step 2: Create a detailed plan based on the analysis",
                ),
                TaskStepDefinition(
                    prompt=f"Step 3: Execute the plan and provide final results",
                ),
            ],
        )
