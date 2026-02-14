from dataclasses import dataclass
import math

from app.db.file_repo import FileRepo
from app.models.model.models import ModelDescription
from app.models.task.enums import ModelCapability
from app.models.task.models import NormalTaskStepDefinition
from app.services.model_cache_service import ModelCacheService
from app.services.model_selection.model_selection_api_service import ModelScoringApiService
from app.services.model_selection.model_evaluation import ModelEvaluation
from app.services.prompt_pricing_service import PromptPricingService
from app.services import config_helpers
from utils import not_none


class TaskModelSelectionError(Exception):
    pass


class TaskModelSelectionService:    
    def __init__(
        self,
        model_cache_service: ModelCacheService,
        file_repo: FileRepo,
        model_scoring_service: ModelScoringApiService,
        pricing_service: PromptPricingService,
    ) -> None:
        self.model_cache_service = model_cache_service
        self.file_repo = file_repo
        self.model_scoring_service = model_scoring_service
        self.pricing_service = pricing_service
    
    async def select_model_for_step(self, step: NormalTaskStepDefinition) -> ModelEvaluation:
        """Select the best model for a step based on score and cost."""
        models = await self.model_cache_service.get_all_models()
        models = self._filter_by_input_modalities(step, models)
        for capability in step.required_capabilities:
            models = self._filter_by_capability(models, capability)

        if len(models) == 0:
            # TODO: This should trigger a reevaluation step
            raise TaskModelSelectionError("No models found that meet requirements")
        
        model_ids = [model.id for model in models]
        evaluations = await self._evaluate_models(model_ids, step)
        return self._select_best_model(evaluations)

    def _filter_by_input_modalities(self, step: NormalTaskStepDefinition, models: list[ModelDescription]) -> list[ModelDescription]:
        """Filter models by input modalities"""
        required_modalities: list[str] = []
        for file_id in step.required_file_ids:
            file_metadata = self.file_repo.get_file_by_id(file_id)
            if file_metadata is None:
                raise TaskModelSelectionError(
                    f"File {file_id} not found for step. This shouldn't happen if validation is correct."
                )
            
            required_modalities.extend(file_metadata.get_required_modalities())

        return [model for model in models if all(modality in model.architecture.input_modalities for modality in required_modalities)]

    def _filter_by_capability(self, models: list[ModelDescription], capability: ModelCapability) -> list[ModelDescription]:
        match capability:
            case ModelCapability.REASONING:
                return [model for model in models if model.supports_reasoning]
            case ModelCapability.EXA_SEARCH:
                return models
            case ModelCapability.NATIVE_WEB_SEARCH:
                return [model for model in models if model.supports_native_web_search]
            case ModelCapability.OCR_PDF:
                return models
            case ModelCapability.TEXT_PDF:
                return models
            case ModelCapability.NATIVE_PDF:
                return [model for model in models if "file" in model.architecture.input_modalities]
            case _:
                raise TaskModelSelectionError(f"Unknown capability: {capability}")
    
    async def _evaluate_models(
        self,
        model_ids: list[str],
        step: NormalTaskStepDefinition,
    ) -> list[ModelEvaluation]:
        """Evaluate models by getting scores, predicted lengths, and estimated costs."""
        try:
            inferences = await self.model_scoring_service.get_model_inferences(
                models_to_score=model_ids,
                prompt=step.prompt
            )
            
            config = config_helpers.build_llm_config_for_capabilities(step.required_capabilities)
            
            file_metadata_list = [
                not_none(self.file_repo.get_file_by_id(file_id), f"File {file_id}")
                for file_id in step.required_file_ids
            ]
            
            # Estimate prompt tokens
            # TODO: Implement proper token counting
            # Rough estimate: 1 token per 4 characters
            estimated_prompt_tokens = len(step.prompt) // 4
            
            # Calculate cost for each inference
            evaluations: list[ModelEvaluation] = []
            for inference in inferences:
                estimated_cost = await self.pricing_service.estimate_response_cost(
                    model_id=inference.model_id,
                    prompt_tokens=estimated_prompt_tokens,
                    predicted_completion_tokens=inference.predicted_length,
                    file_metadata_list=file_metadata_list,
                    config=config,
                )
                
                evaluations.append(ModelEvaluation.from_inference(inference, estimated_cost))
            
            return evaluations
        except Exception as e:
            raise TaskModelSelectionError(
                f"Failed to evaluate models: {str(e)}"
            ) from e
    
    def _select_best_model(self, evaluations: list[ModelEvaluation]) -> ModelEvaluation:
        """
        Select the best model based on normalized score and cost.
        """
        if not evaluations:
            raise TaskModelSelectionError("No models to select from")
        
        if len(evaluations) == 1:
            return evaluations[0]
        
        normalized_entries, median_cost, _ = self._normalize_scores_and_costs(evaluations)

        best_model_id = normalized_entries[0].model_id
        best_utility = float('-inf')
        for normalized in normalized_entries:
            # Filter out extremely expensive models (>3x median) and models with very poor scores (< mean - 2*std)
            if normalized.estimated_cost > 3 * median_cost + 1e-4 or normalized.score < -2:
                continue
            
            # Calculate utility: score / sqrt(cost)
            # Using sqrt makes cost less sensitive to extreme values
            # Add small epsilon to avoid division by zero
            utility = normalized.score / math.sqrt(normalized.cost + 0.01)
            
            if utility > best_utility:
                best_utility = utility
                best_model_id = normalized.model_id

        return next(iter(e for e in evaluations if e.model_id == best_model_id))
    
    def _normalize_scores_and_costs(self, entries: list[ModelEvaluation]) -> tuple[list["_NormalizedEntry"], float, float]:
        """
        Normalize scores and costs to std=1 and mean=0.

        Returns:
            Tuple of (normalized_entries, median_cost, median_score)
        """
        mean_score = sum(entry.score for entry in entries) / len(entries)
        std_score = math.sqrt(sum((entry.score - mean_score) ** 2 for entry in entries) / len(entries))
        mean_cost = sum(entry.estimated_cost for entry in entries) / len(entries)
        std_cost = math.sqrt(sum((entry.estimated_cost - mean_cost) ** 2 for entry in entries) / len(entries))

        median_cost = sorted(entries, key=lambda e: e.estimated_cost)[len(entries) // 2].estimated_cost
        median_score = sorted(entries, key=lambda e: e.score)[len(entries) // 2].score

        normalized_entries = [
            self._NormalizedEntry(
                model_id=entry.model_id,
                score=(entry.score - mean_score) / std_score if std_score > 0 else 0,
                cost=(entry.estimated_cost - mean_cost) / std_cost if std_cost > 0 else 0,
            )
            for entry in entries
        ]

        return normalized_entries, median_cost, median_score

    @dataclass
    class _NormalizedEntry:
        model_id: str
        score: float
        cost: float
