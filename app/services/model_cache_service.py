from datetime import datetime, timedelta, timezone
import httpx

from app.models.model.models import ModelDescription, ModelPricing, ModelArchitecture


CACHE_DURATION_SECONDS = 86400 # 1 day


class ModelCacheService:
    """Service for caching model information from OpenRouter"""
    
    def __init__(self) -> None:
        self._cache: tuple[list[ModelDescription], datetime] | None = None
    
    def _invalidate_cache_if_needed(self) -> None:
        """Invalidate the cache if it has expired"""
        if self._cache is None:
            return
        
        _, cache_timestamp = self._cache
        now = datetime.now(timezone.utc)
        cache_age = now - cache_timestamp
        
        if cache_age >= timedelta(seconds=CACHE_DURATION_SECONDS):
            self._cache = None
    
    def _parse_model_description(self, model_data: dict) -> ModelDescription:
        """Parse a single model from OpenRouter API response"""
        model_id = model_data.get("id", "")
        model_provider = model_id.split("/")[0] if "/" in model_id else ""

        # Extract pricing information
        pricing_data = model_data.get("pricing", {})
        input_cost = float(pricing_data.get("prompt", 0))
        output_cost = float(pricing_data.get("completion", 0))
        
        # Exa search default: $4 per 1000 results
        web_search_price = float(pricing_data.get("web_search", 0)) if pricing_data.get("web_search") else None
        exa_search_price = 4.0 if web_search_price is None else (web_search_price * 1000.0 if web_search_price > 0 else None)
        native_search_price = (web_search_price * 1000.0 if web_search_price and web_search_price > 0 else exa_search_price) if web_search_price is not None else exa_search_price
        
        # OpenRouter returns cost per token, convert to per million
        pricing = ModelPricing(
            prompt_per_million=input_cost * 1_000_000,
            completion_per_million=output_cost * 1_000_000,
            request=float(pricing_data["request"]) if pricing_data.get("request") and float(pricing_data["request"]) > 0 else None,
            image=float(pricing_data["image"]) if pricing_data.get("image") and float(pricing_data["image"]) > 0 else None,
            audio=float(pricing_data["audio"]) * 1_000_000 if pricing_data.get("audio") and float(pricing_data["audio"]) > 0 else None,
            internal_reasoning=float(pricing_data["internal_reasoning"]) * 1_000_000 if pricing_data.get("internal_reasoning") and float(pricing_data["internal_reasoning"]) > 0 else None,
            exa_search=exa_search_price,
            native_search=native_search_price,
        )
        
        # Extract architecture information
        arch_data = model_data.get("architecture", {})
        architecture = ModelArchitecture(
            modality=arch_data.get("modality", "text->text"),
            input_modalities=arch_data.get("input_modalities", ["text"]),
            output_modalities=arch_data.get("output_modalities", ["text"]),
            tokenizer=arch_data.get("tokenizer", "Other"),
        )
        
        # Extract provider information
        top_provider = model_data.get("top_provider", {})
        is_moderated = top_provider.get("is_moderated", False)
        
        return ModelDescription(
            id=model_id,
            name=model_data.get("name", model_id),
            provider=model_provider,
            description=model_data.get("description", ""),
            context_length=model_data.get("context_length", 0),
            architecture=architecture,
            pricing=pricing,
            is_moderated=is_moderated,
            supported_parameters=model_data.get("supported_parameters", []),
        )
    
    async def _fetch_models_from_api(self) -> list[ModelDescription]:
        """Fetch all models from OpenRouter API"""
        async with httpx.AsyncClient() as client:
            response = await client.get("https://openrouter.ai/api/v1/models")
            response.raise_for_status()
            data = response.json()
        
        models = []
        for model_data in data.get("data", []):
            models.append(self._parse_model_description(model_data))
        
        return models
    
    async def get_all_models(self, provider: str | None = None) -> list[ModelDescription]:
        """
        Get all available models, using cache if available and valid.
        """
        self._invalidate_cache_if_needed()
        if self._cache is not None:
            models, _ = self._cache
        else:
            models = await self._fetch_models_from_api()
            self._cache = (models, datetime.now(timezone.utc))
        
        # Filter by provider if requested
        if provider is not None:
            models = [m for m in models if m.provider == provider]
        
        return models
    
    async def get_model_by_id(self, model_id: str) -> ModelDescription | None:
        """Get a specific model by ID"""
        models = await self.get_all_models()
        return next((m for m in models if m.id == model_id), None)
