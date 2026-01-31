from app.services.llm.llm_message import LlmMessage
from app.services.llm.llm_file import LlmFileBase
from app.services.model_cache_service import ModelCacheService


class PromptPricingService:
    """Service for calculating prompt pricing based on model usage"""

    def __init__(self, model_cache_service: ModelCacheService) -> None:
        self.model_cache_service = model_cache_service

    async def calculate_cost(
        self,
        model_id: str,
        llm_message: LlmMessage,
        files: list[LlmFileBase] | None = None,
    ) -> float:
        """
        Calculate the cost for a single LLM request/response.
        
        Args:
            model_id: ID of the model used
            llm_message: The assistant's response message (must have role="assistant")
            files: Optional list of files included in the request
            
        Returns:
            Total cost in USD
        """
        if llm_message.role != "assistant":
            raise ValueError("Cost calculation should only be called for an assistant message with token counts")

        if llm_message.prompt_tokens is None or llm_message.completion_tokens is None:
            raise ValueError("Token counts are not set for assistant message")

        model_description = await self.model_cache_service.get_model_by_id(model_id)
        if model_description is None:
            raise ValueError(f"Model '{model_id}' not found")

        model_pricing = model_description.pricing
        total_cost = 0.0

        # Calculate token costs
        prompt_cost = (llm_message.prompt_tokens / 1_000_000) * model_pricing.prompt_per_million
        completion_cost = (llm_message.completion_tokens / 1_000_000) * model_pricing.completion_per_million
        total_cost += prompt_cost + completion_cost

        # Add per-request cost if applicable
        if model_pricing.request is not None:
            total_cost += model_pricing.request

        # TODO: Improve this - different file types have different costs
        # Add image costs if applicable
        if files and model_pricing.image is not None:
            image_count = sum(1 for f in files if f.type == "image_url")
            total_cost += image_count * model_pricing.image

        # TODO: Add other costs - exa search, native search, etc.

        return total_cost
