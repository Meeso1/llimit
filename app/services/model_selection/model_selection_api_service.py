import httpx

from app.services.model_selection.dtos import InferenceRequest, InferenceResponse
from app.services.model_selection.model_scoring_service_base import ModelScoringServiceBase
from app.services.model_selection.model_evaluation import ModelInference


class ModelScoringApiError(Exception):
    """Exception raised when model scoring API is unavailable or returns errors."""
    pass


class ModelScoringApiService(ModelScoringServiceBase):
    """Service for interacting with the model scoring API."""
    
    def __init__(
        self,
        base_url: str,
        scoring_model: str | None,
        length_prediction_model: str | None,
        batch_size: int
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.scoring_model = scoring_model
        self.length_prediction_model = length_prediction_model
        self.batch_size = batch_size
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
    
    async def get_model_inferences(
        self,
        models_to_score: list[str],
        prompt: str
    ) -> list[ModelInference]:
        """Get inference results (score and predicted length) for models based on a prompt."""
        inference_result = await self._get_inference(models_to_score, [prompt])
        if inference_result.scores is None:
            raise ModelScoringApiError("Scoring model was not configured")
        if inference_result.predicted_lengths is None:
            raise ModelScoringApiError("Length prediction model was not configured")
        
        # Convert to list of ModelInference
        inferences = []
        for model_id in models_to_score:
            inferences.append(ModelInference(
                model_id=model_id,
                score=inference_result.scores[model_id][0],
                predicted_length=inference_result.predicted_lengths[model_id][0],
            ))
        return inferences
    
    async def _get_inference(
        self,
        models_to_score: list[str],
        prompts: list[str]
    ) -> InferenceResponse:
        """Get inference results (scores and/or lengths) for models based on prompts."""
        request = InferenceRequest(
            scoring_model=self.scoring_model,
            length_prediction_model=self.length_prediction_model,
            model_names=models_to_score,
            prompts=prompts,
            batch_size=self.batch_size
        )
        
        try:
            response = await self.client.post(
                f"{self.base_url}/infer",
                json=request.model_dump()
            )
            response.raise_for_status()
            
            return InferenceResponse.model_validate(response.json())
        except httpx.HTTPError as e:
            # Call `/health` so that we get a better error message if it throws
            await self.health_check()
            
            # If health check passed, the issue is with the specific request
            raise ModelScoringApiError(
                f"Failed to get inference results from API: {str(e)}"
            ) from e
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
