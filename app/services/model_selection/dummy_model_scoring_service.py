import random
from app.services.model_selection.model_scoring_service_base import ModelScoringServiceBase


class DummyModelScoringService(ModelScoringServiceBase):
    """Dummy implementation of model scoring service for testing."""
    
    async def get_model_scores(
        self,
        models_to_score: list[str],
        prompts: list[str],
        batch_size: int = 128
    ) -> dict[str, list[float]]:
        """Get dummy scores for models."""
        gemini_flash = "google/gemini-2.5-flash-lite"
        
        if gemini_flash in models_to_score:
            return {
                model_id: [1.0 if model_id == gemini_flash else -1.0 for _ in prompts]
                for model_id in models_to_score
            }
        else:
            return {
                model_id: [random.uniform(-1.0, 1.0) for _ in prompts]
                for model_id in models_to_score
            }
