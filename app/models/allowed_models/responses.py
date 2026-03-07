from pydantic import BaseModel


class AllowedModelsResponse(BaseModel):
    """Response containing the current list of allowed model IDs"""

    model_ids: list[str]
