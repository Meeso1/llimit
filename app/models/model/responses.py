from pydantic import BaseModel


class ModelDescriptionResponse(BaseModel):
    name: str
    description: str
    provider: str
    context_length: int
    input_cost_per_million: float
    output_cost_per_million: float


class ModelsListResponse(BaseModel):
    models: list[ModelDescriptionResponse]

