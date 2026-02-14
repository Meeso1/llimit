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
    internal_reasoning: float | None = None  # Cost for reasoning tokens (per million)
    exa_search: float | None = None  # Cost per 1000 Exa search results
    native_search: float | None = None  # Cost per 1000 native web search requests

    # pdf-text is free, and produces text that is then included in the prompt
    # native pdf processing is counted as input tokens too, at the same price
    pdf_mistral_ocr: float = 0.0002 # Per 1000 pages

    # Video pricing data isn't available through OpenRouter

    def to_response(self) -> ModelPricingResponse:
        return ModelPricingResponse(
            prompt_per_million=self.prompt_per_million,
            completion_per_million=self.completion_per_million,
            request=self.request,
            image=self.image,
            audio=self.audio,
            internal_reasoning=self.internal_reasoning,
            exa_search=self.exa_search,
            native_search=self.native_search,
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

    @property
    def supports_reasoning(self) -> bool:
        """Whether the model supports extended thinking/reasoning"""
        return "reasoning" in self.supported_parameters or "include_reasoning" in self.supported_parameters

    @property
    def supports_tools(self) -> bool:
        """Whether the model supports tool/function calling"""
        return "tools" in self.supported_parameters or "tool_choice" in self.supported_parameters

    @property
    def supports_structured_outputs(self) -> bool:
        """Whether the model supports structured output formats"""
        return "structured_outputs" in self.supported_parameters

    @property
    def supports_native_web_search(self) -> bool:
        """Whether the model supports native web search via web_search_options parameter"""
        # TODO: Verify and improve
        if self.id.startswith("google/gemini-2.5-"):
            return True

        if self.id.startswith("perplexity/"):
            return True

        return "web_search_options" in self.supported_parameters

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
            supports_reasoning=self.supports_reasoning,
            supports_tools=self.supports_tools,
            supports_structured_outputs=self.supports_structured_outputs,
            supports_native_web_search=self.supports_native_web_search,
        )

