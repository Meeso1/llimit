# TODO: Complete implementation
from app.models.task.models import NormalTaskStepDefinition


class TaskModelSelectionService:    
    def __init__(self) -> None:
        pass
    
    def select_model_for_step(
        self,
        step: NormalTaskStepDefinition
    ) -> str:
        # TODO: Implement intelligent model selection
        # The selection should consider:
        # 1. Parse step_prompt to infer requirements if not provided
        # 2. Match requirements to model capabilities
        # 3. Balance performance vs cost
        # 4. Consider model strengths (e.g., Claude for writing, GPT-4 for reasoning)
        
        return "google/gemini-2.5-flash-lite"
