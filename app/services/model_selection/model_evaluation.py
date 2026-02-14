from dataclasses import dataclass


@dataclass
class ModelInference:
    """Inference result for a single model (score and predicted length)."""
    model_id: str
    score: float
    predicted_length: float


@dataclass
class ModelEvaluation:
    """Complete evaluation of a model including cost estimation."""
    model_id: str
    score: float
    predicted_length: float
    estimated_cost: float

    @classmethod
    def from_inference(cls, inference: ModelInference, estimated_cost: float) -> "ModelEvaluation":
        """Create a ModelEvaluation from a ModelInference by adding cost."""
        return cls(
            model_id=inference.model_id,
            score=inference.score,
            predicted_length=inference.predicted_length,
            estimated_cost=estimated_cost,
        )
