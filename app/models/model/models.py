from dataclasses import dataclass

from app.models.model.responses import (
    ModelPricingResponse,
    ModelArchitectureResponse,
    ModelDescriptionResponse,
)


@dataclass
class ModelPricing:
    """Pricing information for a model"""
    # Cost per token (already converted to per-million for convenience)
    prompt_per_million: float  # Input tokens
    completion_per_million: float  # Output tokens
    
    # Optional additional costs
    request: float | None = None  # Cost per request
    image: float | None = None  # Cost per image
    audio: float | None = None  # Cost per audio token (per million)
    web_search: float | None = None  # Cost for web search feature
    internal_reasoning: float | None = None  # Cost for reasoning tokens (per million)
    input_cache_read: float | None = None  # Cost per million cached input tokens read
    input_cache_write: float | None = None  # Cost per million cached input tokens written

    def to_response(self) -> ModelPricingResponse:
        return ModelPricingResponse(
            prompt_per_million=self.prompt_per_million,
            completion_per_million=self.completion_per_million,
            request=self.request,
            image=self.image,
            audio=self.audio,
            web_search=self.web_search,
            internal_reasoning=self.internal_reasoning,
            input_cache_read=self.input_cache_read,
            input_cache_write=self.input_cache_write,
        )


@dataclass
class ModelArchitecture:
    """Architecture and capabilities information for a model"""
    modality: str  # e.g. "text->text", "text+image->text"
    input_modalities: list[str]  # e.g. ["text", "image", "file", "audio"]
    output_modalities: list[str]  # e.g. ["text"]
    tokenizer: str  # e.g. "GPT", "Claude", "Other"

    def to_response(self) -> ModelArchitectureResponse:
        return ModelArchitectureResponse(
            modality=self.modality,
            input_modalities=self.input_modalities,
            output_modalities=self.output_modalities,
            tokenizer=self.tokenizer,
        )


@dataclass
class ModelDescription:
    """Complete description of an LLM model"""
    id: str  # Full model ID (e.g. "openai/gpt-4")
    name: str  # Human-readable name
    provider: str  # Provider name (e.g. "openai", "anthropic")
    description: str  # Model description
    context_length: int  # Maximum context length in tokens
    architecture: ModelArchitecture
    pricing: ModelPricing
    is_moderated: bool  # Whether the model has content moderation
    supported_parameters: list[str]  # List of supported API parameters

    def to_response(self) -> ModelDescriptionResponse:
        return ModelDescriptionResponse(
            id=self.id,
            name=self.name,
            provider=self.provider,
            description=self.description,
            context_length=self.context_length,
            architecture=self.architecture.to_response(),
            pricing=self.pricing.to_response(),
            is_moderated=self.is_moderated,
            supported_parameters=self.supported_parameters,
        )

