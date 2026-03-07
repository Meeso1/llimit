from fastapi import APIRouter, status

from app.api.dependencies import AllowedModelsRepoDep, AuthContextDep
from app.models.allowed_models.requests import SetAllowedModelsRequest
from app.models.allowed_models.responses import AllowedModelsResponse

router = APIRouter(
    prefix="/allowed-models",
    tags=["allowed-models"],
)


@router.get("", response_model=AllowedModelsResponse, status_code=status.HTTP_200_OK)
async def get_allowed_models(
    context: AuthContextDep(require_openrouter_key=False),
    allowed_models_repo: AllowedModelsRepoDep,
) -> AllowedModelsResponse:
    return AllowedModelsResponse(model_ids=allowed_models_repo.get_all())


@router.put("", response_model=AllowedModelsResponse, status_code=status.HTTP_200_OK)
async def set_allowed_models(
    request_body: SetAllowedModelsRequest,
    context: AuthContextDep(require_openrouter_key=False),
    allowed_models_repo: AllowedModelsRepoDep,
) -> AllowedModelsResponse:
    allowed_models_repo.set_all(request_body.model_ids)
    return AllowedModelsResponse(model_ids=request_body.model_ids)
