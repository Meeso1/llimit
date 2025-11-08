from datetime import datetime, timedelta, timezone

from app.services.llm_service_base import LlmService, ModelDescription


CACHE_DURATION_SECONDS = 86400 # 1 day


class ModelCacheService:
    """Service for caching model information from OpenRouter"""
    
    def __init__(self, llm_service: LlmService) -> None:
        self._llm_service = llm_service
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
    
    async def get_all_models(self, provider: str | None = None) -> list[ModelDescription]:
        """
        Get all available models, using cache if available and valid.
        """
        self._invalidate_cache_if_needed()
        if self._cache is not None:
            models, _ = self._cache
        else:
            models = await self._llm_service.get_models(provider=None)
            self._cache = (models, datetime.now(timezone.utc))
        
        # Filter by provider if requested
        if provider is not None:
            models = [m for m in models if m.provider == provider]
        
        return models
