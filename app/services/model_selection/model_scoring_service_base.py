from abc import ABC, abstractmethod

from app.services.model_selection.model_evaluation import ModelInference


class ModelScoringServiceBase(ABC):
    """Base class for model scoring services."""
    
    @abstractmethod
    async def get_model_inferences(
        self,
        models_to_score: list[str],
        prompt: str
    ) -> list[ModelInference]:
        """Get inference results (score and predicted length) for models based on a prompt."""
        pass
