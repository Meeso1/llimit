from pydantic import BaseModel


class SetAllowedModelsRequest(BaseModel):
    """Request body for replacing the allowed-models list"""

    model_ids: list[str]
