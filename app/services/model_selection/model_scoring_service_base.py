from abc import ABC, abstractmethod


class ModelScoringServiceBase(ABC):
    """Base class for model scoring services."""
    
    @abstractmethod
    async def get_model_scores(
        self,
        models_to_score: list[str],
        prompts: list[str],
        batch_size: int = 128
    ) -> dict[str, list[float]]:
        """Get scores for models based on prompts."""
        pass
