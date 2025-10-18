from fastapi import APIRouter, Request, status

from app.api.dependencies import LLMServiceDep, AuthServiceDep
from app.models.model.responses import ModelsListResponse, ModelDescriptionResponse

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("", response_model=ModelsListResponse, status_code=status.HTTP_200_OK)
async def list_models(
    request: Request,
    llm_service: LLMServiceDep,
    auth_service: AuthServiceDep,
) -> ModelsListResponse:
    """
    Get a list of available LLM models with their descriptions and pricing.
    """
    auth_service.authenticate(request, require_openrouter_key=False)
    
    models = await llm_service.get_models()
    
    return ModelsListResponse(
        models=[
            ModelDescriptionResponse(
                name=model.name,
                description=model.description,
                provider=model.provider,
                context_length=model.context_length,
                input_cost_per_million=model.input_cost_per_million,
                output_cost_per_million=model.output_cost_per_million,
            )
            for model in models
        ]
    )

