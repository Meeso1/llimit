import httpx
from app.services.model_selection.dtos import ModelScoringRequest, ModelScoringResponse
from app.services.model_selection.model_scoring_service_base import ModelScoringServiceBase


class ModelScoringApiError(Exception):
    """Exception raised when model scoring API is unavailable or returns errors."""
    pass


class ModelScoringApiService(ModelScoringServiceBase):
    """Service for interacting with the model scoring API."""
    
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def health_check(self) -> None:
        """Check if the model scoring API is reachable."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ModelScoringApiError(
                f"Model scoring API is not reachable at {self.base_url}: {str(e)}"
            ) from e
    
    async def get_model_scores(
        self,
        models_to_score: list[str],
        prompts: list[str],
        batch_size: int = 128
    ) -> dict[str, list[float]]:
        """Get scores for models based on prompts."""
        request = ModelScoringRequest(
            model=self.model,
            models_to_score=models_to_score,
            prompts=prompts,
            batch_size=batch_size
        )
        
        try:
            response = await self.client.get(
                f"{self.base_url}/infer",
                params=request.model_dump()
            )
            response.raise_for_status()
            
            scoring_response = ModelScoringResponse.model_validate(response.json())
            return scoring_response.scores
        except httpx.HTTPError as e:
            # Call `/health` so that we get a better error message if it throws
            await self.health_check()
            
            # If health check passed, the issue is with the specific request
            raise ModelScoringApiError(
                f"Failed to get model scores from API: {str(e)}"
            ) from e
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
