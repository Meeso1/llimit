from pydantic import BaseModel


class ModelPricingResponse(BaseModel):
    prompt_per_million: float
    completion_per_million: float
    request: float | None = None
    image: float | None = None
    audio: float | None = None
    internal_reasoning: float | None = None


class ModelArchitectureResponse(BaseModel):
    modality: str
    input_modalities: list[str]
    output_modalities: list[str]
    tokenizer: str


class ModelDescriptionResponse(BaseModel):
    id: str
    name: str
    provider: str
    description: str
    context_length: int
    architecture: ModelArchitectureResponse
    pricing: ModelPricingResponse
    is_moderated: bool
    supported_parameters: list[str]
    
    # Computed capability flags
    supports_reasoning: bool
    supports_tools: bool
    supports_structured_outputs: bool


class ModelsListResponse(BaseModel):
    models: list[ModelDescriptionResponse]

