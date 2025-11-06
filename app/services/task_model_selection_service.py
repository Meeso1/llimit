from dataclasses import dataclass
from enum import Enum


class ModelCapability(str, Enum):
    """Capabilities that different models might have"""
    WEB_SEARCH = "web_search"
    IMAGE_GENERATION = "image_generation"
    IMAGE_UNDERSTANDING = "image_understanding"
    CODE_EXECUTION = "code_execution"
    REASONING = "reasoning"
    CREATIVITY = "creativity"
    INSTRUCTION_FOLLOWING = "instruction_following"


class StepKind(str, Enum):
    """Different kinds of steps that require different model characteristics"""
    CREATIVE = "creative"  # Writing, brainstorming, design
    ANALYTICAL = "analytical"  # Analysis, research, reasoning
    STRUCTURED = "structured"  # Following precise instructions, formatting
    CODING = "coding"  # Programming tasks
    RESEARCH = "research"  # Information gathering


@dataclass
class StepRequirements:
    """Requirements for a task step"""
    complexity: str  # "low", "medium", "high"
    required_capabilities: list[ModelCapability]
    step_kind: StepKind


# TODO: Complete implementation
class TaskModelSelectionService:
    """
    Service responsible for selecting the appropriate LLM model for each step.
    
    This service analyzes step requirements and selects models based on:
    - Step complexity
    - Required capabilities (web search, image support, etc.)
    - Step kind (creative vs analytical vs structured)
    - Cost considerations
    - Model performance characteristics
    """
    
    def __init__(self) -> None:
        pass
    
    def select_model_for_step(
        self,
        step_prompt: str,
        step_requirements: StepRequirements | None = None,
    ) -> str:
        """
        Select the most appropriate model for a given step.
        
        Args:
            step_prompt: The prompt for this specific step
            step_requirements: Optional explicit requirements for this step
            
        Returns:
            Model identifier string (e.g., "openai/gpt-4o")
        """
        # TODO: Implement intelligent model selection
        # The selection should consider:
        # 1. Parse step_prompt to infer requirements if not provided
        # 2. Match requirements to model capabilities
        # 3. Balance performance vs cost
        # 4. Consider model strengths (e.g., Claude for writing, GPT-4 for reasoning)
        
        # Temporary hardcoded implementation for testing
        # Simple keyword-based selection
        prompt_lower = step_prompt.lower()
        
        if "analyze" in prompt_lower or "analysis" in prompt_lower:
            return "openai/gpt-4o"  # Use smarter model for analysis
        elif "plan" in prompt_lower or "planning" in prompt_lower:
            return "anthropic/claude-3.5-sonnet"  # Claude for planning
        else:
            return "openai/gpt-4o-mini"  # Default cheaper model
    
    def analyze_step_requirements(self, step_prompt: str) -> StepRequirements:
        """
        Analyze a step prompt to determine its requirements.
        
        Args:
            step_prompt: The prompt to analyze
            
        Returns:
            StepRequirements with inferred requirements
        """
        # TODO: Implement prompt analysis
        # This could use:
        # - Keyword detection (e.g., "search for", "create image", "write code")
        # - Complexity heuristics (length, technical terms)
        # - Intent classification
        
        return StepRequirements(
            complexity="medium",
            required_capabilities=[],
            step_kind=StepKind.ANALYTICAL,
        )

