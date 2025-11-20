from random import random
from app.db.file_repo import FileRepo
from app.models.model.models import ModelDescription
from app.models.task.enums import ModelCapability
from app.models.task.models import NormalTaskStepDefinition
from app.services.model_cache_service import ModelCacheService


class TaskModelSelectionError(Exception):
    pass


class TaskModelSelectionService:    
    def __init__(self, model_cache_service: ModelCacheService, file_repo: FileRepo) -> None:
        self.model_cache_service = model_cache_service
        self.file_repo = file_repo
    
    def select_model_for_step(
        self,
        step: NormalTaskStepDefinition
    ) -> str:
        models = self.model_cache_service.get_all_models()
        models = self._filter_by_input_modalities(step, models)
        for capability in step.required_capabilities:
            models = self._filter_by_capability(models, capability)

        if len(models) == 0:
            # TODO: This should trigger a reevaluation step
            raise TaskModelSelectionError("No models found that meet requirements")
        
        # TODO: Implement scoring etc.

        model_ids = [model.id for model in models]
        if "google/gemini-2.5-flash-lite" in model_ids:
            return "google/gemini-2.5-flash-lite"

        elif "google/gemini-2.5-pro" in model_ids:
            return "google/gemini-2.5-pro"
        
        return random.choice(model_ids)

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
            case _:
                raise TaskModelSelectionError(f"Unknown capability: {capability}")
