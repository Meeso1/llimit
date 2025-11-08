from fastapi import APIRouter, status
from fastapi.params import Query

from app.api.dependencies import ModelCacheServiceDep, AuthContextDep
from app.models.model.responses import ModelsListResponse

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("", response_model=ModelsListResponse, status_code=status.HTTP_200_OK)
async def list_models(
    context: AuthContextDep(require_openrouter_key=False),
    model_cache_service: ModelCacheServiceDep,
    provider: str | None = Query(None, description="Filter models by provider"),
) -> ModelsListResponse:
    """
    Get a list of available LLM models with their descriptions and pricing.
    
    Results are cached for performance. The cache is automatically refreshed
    after expiration.
    """
    models = await model_cache_service.get_all_models(provider=provider)
    
    return ModelsListResponse(
        models=[model.to_response() for model in models]
    )
