from app.db.file_repo import FileRepo
from app.models.model.models import ModelDescription
from app.models.task.enums import ModelCapability
from app.models.task.models import NormalTaskStepDefinition
from app.services.model_cache_service import ModelCacheService
from app.services.model_selection.model_scoring_service_base import ModelScoringServiceBase


class TaskModelSelectionError(Exception):
    pass


class TaskModelSelectionService:    
    def __init__(
        self,
        model_cache_service: ModelCacheService,
        file_repo: FileRepo,
        model_scoring_service: ModelScoringServiceBase
    ) -> None:
        self.model_cache_service = model_cache_service
        self.file_repo = file_repo
        self.model_scoring_service = model_scoring_service
    
    async def select_model_for_step(
        self,
        step: NormalTaskStepDefinition
    ) -> str:
        models = await self.model_cache_service.get_all_models()
        models = self._filter_by_input_modalities(step, models)
        for capability in step.required_capabilities:
            models = self._filter_by_capability(models, capability)

        if len(models) == 0:
            # TODO: This should trigger a reevaluation step
            raise TaskModelSelectionError("No models found that meet requirements")
        
        model_ids = [model.id for model in models]
        return await self._score_and_select_best_model(model_ids, step)

    def _filter_by_input_modalities(self, step: NormalTaskStepDefinition, models: list[ModelDescription]) -> list[ModelDescription]:
        """Filter models by input modalities"""
        required_modalities: list[str] = []
        for file_id in step.required_file_ids:
            file_metadata = self.file_repo.get_file_by_id(file_id)
            if file_metadata is None:
                raise TaskModelSelectionError(
                    f"File {file_id} not found for step {step.id}. This shouldn't happen if validation is correct."
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
    
    async def _score_and_select_best_model(
        self,
        model_ids: list[str],
        step: NormalTaskStepDefinition
    ) -> str:
        """Score models using the API and select the best one."""
        try:
            scores = await self.model_scoring_service.get_model_scores(
                models_to_score=model_ids,
                prompts=[step.prompt]
            )
            
            # TODO: Take costs into account
            best_model, _ = max(scores.items(), key=lambda x: x[1][0])
            return best_model
        except Exception as e:
            raise TaskModelSelectionError(
                f"Failed to select model: {str(e)}"
            ) from e
