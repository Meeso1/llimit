import random

from app.services.model_selection.model_scoring_service_base import ModelScoringServiceBase
from app.services.model_selection.model_evaluation import ModelInference


class DummyModelScoringService(ModelScoringServiceBase):
    """Dummy implementation of model scoring service for testing."""
    
    async def get_model_inferences(
        self,
        models_to_score: list[str],
        prompt: str
    ) -> list[ModelInference]:
        """Get dummy inference results for models."""
        gemini_flash = "google/gemini-2.5-flash-lite"
        
        inferences = []
        for model_id in models_to_score:
            if gemini_flash in models_to_score:
                score = 1.0 if model_id == gemini_flash else -1.0
            else:
                score = random.uniform(-1.0, 1.0)
            
            predicted_length = random.uniform(100.0, 500.0)
            
            inferences.append(ModelInference(
                model_id=model_id,
                score=score,
                predicted_length=predicted_length,
            ))
        
        return inferences
