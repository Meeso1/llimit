from app.models.file.models import AudioType, FileMetadata, ImageType, VideoType
from app.models.model.models import ModelPricing
from app.services.llm.config.pdf_config import PdfConfig
from app.services.llm.config.web_search_config import SearchContextSize
from app.services.llm.llm_message import LlmMessage
from app.services.llm.config.llm_config import LlmConfig
from app.services.llm.config.reasoning_config import ReasoningEffort
from app.services.model_cache_service import ModelCacheService


class PromptPricingService:
    """Service for calculating prompt pricing based on model usage"""

    def __init__(self, model_cache_service: ModelCacheService) -> None:
        self.model_cache_service = model_cache_service

    async def calculate_cost(
        self,
        model_id: str,
        llm_message: LlmMessage,
        file_metadata_list: list[FileMetadata],
        config: LlmConfig,
    ) -> float:
        """
        Calculate the cost for a single LLM request/response.
        
        Args:
            model_id: ID of the model used
            llm_message: The assistant's response message (must have role="assistant")
            file_metadata_list: List of file metadata for files included in the request
            config: LLM configuration used for the request
            
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

        return self._calculate_cost_internal(
            prompt_tokens=llm_message.prompt_tokens,
            completion_tokens=llm_message.completion_tokens,
            file_metadata_list=file_metadata_list,
            config=config,
            model_pricing=model_pricing,
            omit_token_costs=True, # Cost of thigns included in the prompt etc. is already included in the prompt tokens
        )

    async def estimate_response_cost(
        self,
        model_id: str,
        prompt_tokens: int,
        predicted_completion_tokens: float,
        file_metadata_list: list[FileMetadata],
        config: LlmConfig,
    ) -> float:
        """
        Estimate the cost for a potential LLM request/response before making the call.
        
        Args:
            model_id: ID of the model to use
            prompt_tokens: Number of tokens in the prompt
            predicted_completion_tokens: Predicted number of completion tokens
            file_metadata_list: List of file metadata for files included in the request
            config: LLM configuration (reasoning, web search, etc.)
            
        Returns:
            Estimated total cost in USD
        """
        model_description = await self.model_cache_service.get_model_by_id(model_id)
        if model_description is None:
            raise ValueError(f"Model '{model_id}' not found")

        model_pricing = model_description.pricing

        return self._calculate_cost_internal(
            prompt_tokens=prompt_tokens,
            completion_tokens=predicted_completion_tokens,
            file_metadata_list=file_metadata_list,
            config=config,
            model_pricing=model_pricing,
            omit_token_costs=False, # Compute estimated token counts and their costs
        )

    def _calculate_cost_internal(
        self,
        prompt_tokens: float,
        completion_tokens: float,
        file_metadata_list: list[FileMetadata],
        config: LlmConfig,
        model_pricing: ModelPricing,
        omit_token_costs: bool
    ) -> float:
        """
        Internal method to calculate cost with given parameters.
        Shared logic between actual cost calculation and estimation.
        """
        total_cost = 0.0

        # Calculate base token costs
        prompt_cost = (prompt_tokens / 1_000_000) * model_pricing.prompt_per_million
        completion_cost = (completion_tokens / 1_000_000) * model_pricing.completion_per_million
        total_cost += prompt_cost + completion_cost

        # Add per-request cost if applicable
        if model_pricing.request is not None:
            total_cost += model_pricing.request

        # Add file costs
        total_cost += self._calculate_file_costs(file_metadata_list, model_pricing, config, omit_token_costs)

        # Add configuration-based costs (reasoning, web search, etc.)
        total_cost += self._calculate_reasoning_cost(completion_tokens, config, model_pricing)
        total_cost += self._calculate_web_search_cost(config, model_pricing)

        return total_cost

    def _calculate_file_costs(
        self, 
        file_metadata_list: list[FileMetadata], 
        model_pricing: ModelPricing, 
        config: LlmConfig, 
        omit_token_costs: bool
    ) -> float:
        """Calculate costs for attached files based on their metadata."""
        if not file_metadata_list:
            return 0.0

        cost = 0.0

        for file_metadata in file_metadata_list:
            if file_metadata.is_pdf():
                cost += self._calculate_pdf_cost(file_metadata, model_pricing, config.pdf, omit_token_costs)
            elif file_metadata.is_text_file():
                cost += self._calculate_text_file_cost(file_metadata, model_pricing, omit_token_costs)
            elif (image_type := file_metadata.get_image_type()) is not None:
                cost += self._calculate_image_cost(image_type, file_metadata, model_pricing)
            elif (video_type := file_metadata.get_video_type()) is not None:
                cost += self._calculate_video_cost(video_type, file_metadata, model_pricing, omit_token_costs)
            elif (audio_type := file_metadata.get_audio_type()) is not None:
                cost += self._calculate_audio_cost(audio_type, file_metadata, model_pricing, omit_token_costs)
            else:
                raise ValueError(f"Unsupported file type: {file_metadata.content_type}")

    def _calculate_image_cost(self, image_type: ImageType, metadata: FileMetadata, model_pricing: ModelPricing) -> float:
        return model_pricing.image or 0.0 # images are priced per image, regardless of size

    def _calculate_video_cost(
        self, 
        video_type: VideoType, 
        metadata: FileMetadata, 
        model_pricing: ModelPricing, 
        omit_token_costs: bool
    ) -> float:
        if omit_token_costs:
            return 0.0 # Video is priced as input tokens

        return 10 * (model_pricing.image or 0.0) # Video pricing data isn't available through OpenRouter

    def _calculate_audio_cost(
        self, 
        audio_type: AudioType, 
        metadata: FileMetadata, 
        model_pricing: ModelPricing
    ) -> float:
        if model_pricing.audio is None:
            return 0.0

        if metadata.size_bytes is None:
            raise ValueError("Audio file metadata has no size - this shouldn't happen because audio URLs are not supported")
        
        # TODO: Get actual audio length in file metadata
        mb_per_minute = {
            "wav": 10,
            "mp3": 1.2,
        }[audio_type]
        estimated_length_minutes = metadata.size_bytes / (1024 * 1024) / mb_per_minute

        estimated_tokens_per_minute = 75 * 60 # 75 tokens per second * 60 seconds per minute
        estimated_audio_tokens = estimated_length_minutes * estimated_tokens_per_minute
        return (estimated_audio_tokens / 1_000_000) * model_pricing.audio

    def _calculate_pdf_cost(
        self, 
        metadata: FileMetadata,
        model_pricing: ModelPricing, 
        pdf_config: PdfConfig, 
        omit_token_costs: bool
    ) -> float:
        # TODO: We need page count, text token count, and file token count for pricing
        
        return 0.0 

    def _calculate_text_file_cost(
        self, 
        metadata: FileMetadata, 
        model_pricing: ModelPricing, 
        omit_token_costs: bool
    ) -> float:
        if omit_token_costs:
            return 0.0 # Text files are included in the prompt

        if metadata.size_bytes is None:
            raise ValueError("Text file metadata has no size - this shouldn't happen because text file URLs are not supported")
        
        bytes_per_character = 1.5 # Assuming UTF-8 encoding
        characters = metadata.size_bytes / bytes_per_character
        characters_per_token = 4
        tokens = characters / characters_per_token
        return (tokens / 1_000_000) * model_pricing.prompt_per_million # Text files are just included in the prompt

    def _calculate_reasoning_cost(
        self,
        completion_tokens: float,
        config: LlmConfig,
        model_pricing: ModelPricing
    ) -> float:
        """Calculate estimated cost for reasoning tokens."""
        if not config.reasoning.is_enabled() or model_pricing.internal_reasoning is None:
            return 0.0

        # Estimate reasoning tokens based on effort level
        reasoning_multiplier = {
            ReasoningEffort.NONE: 0.0,
            ReasoningEffort.MINIMAL: 0.5,
            ReasoningEffort.LOW: 1.0,
            ReasoningEffort.MEDIUM: 2.0,
            ReasoningEffort.HIGH: 4.0,
        }[config.reasoning.effort]

        estimated_reasoning_tokens = completion_tokens * reasoning_multiplier
        return (estimated_reasoning_tokens / 1_000_000) * model_pricing.internal_reasoning

    def _calculate_web_search_cost(self, config: LlmConfig, model_pricing: ModelPricing) -> float:
        """Calculate estimated cost for web search."""
        cost = 0.0

        # Exa search cost
        if config.web_search.use_exa_search and model_pricing.exa_search is not None:
            estimated_results = config.web_search.max_results # exa should pretty much always use max results
            cost += (estimated_results / 1000.0) * model_pricing.exa_search # priced per 1000 results

        # Native web search cost
        if config.web_search.use_native_search and model_pricing.native_search is not None:
            estimated_results = config.web_search.max_results # TODO: 'max_results' is for Exa search.Maybe get actual number somehow?
            multiplier = {
                SearchContextSize.LOW: 0.5,
                SearchContextSize.MEDIUM: 1.0,
                SearchContextSize.HIGH: 2.0,
            }[config.web_search.search_context_size]
            cost += (estimated_results * multiplier / 1000.0) * model_pricing.native_search # priced per 1000 requests

        return cost
