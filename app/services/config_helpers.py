from app.models.task.enums import ModelCapability
from app.services.llm.config.llm_config import LlmConfig
from app.services.llm.config.reasoning_config import ReasoningConfig
from app.services.llm.config.web_search_config import WebSearchConfig, SearchContextSize
from app.services.llm.config.pdf_config import PdfConfig, PdfEngine


def build_llm_config_for_capabilities(required_capabilities: list[ModelCapability]) -> LlmConfig:
    """Build LLM configuration based on required capabilities."""
    return LlmConfig(
        web_search=build_web_search_config_for_capabilities(required_capabilities),
        reasoning=build_reasoning_config_for_capabilities(required_capabilities),
        pdf=build_pdf_config_for_capabilities(required_capabilities),
    )


def build_web_search_config_for_capabilities(required_capabilities: list[ModelCapability]) -> WebSearchConfig:
    """Build web search configuration based on required capabilities."""
    has_exa = ModelCapability.EXA_SEARCH in required_capabilities
    has_native = ModelCapability.NATIVE_WEB_SEARCH in required_capabilities
    
    if not has_exa and not has_native:
        return WebSearchConfig.default()
    
    return WebSearchConfig(
        use_exa_search=has_exa,
        use_native_search=has_native,
        max_results=5,
        search_context_size=SearchContextSize.MEDIUM,
    )


def build_reasoning_config_for_capabilities(required_capabilities: list[ModelCapability]) -> ReasoningConfig:
    """Build reasoning configuration based on required capabilities."""
    has_reasoning = ModelCapability.REASONING in required_capabilities
    
    if not has_reasoning:
        return ReasoningConfig.default()
    
    return ReasoningConfig.with_medium_effort()


def build_pdf_config_for_capabilities(required_capabilities: list[ModelCapability]) -> PdfConfig:
    """Build PDF configuration based on required capabilities."""
    if ModelCapability.OCR_PDF in required_capabilities:
        return PdfConfig(engine=PdfEngine.MISTRAL_OCR)
    elif ModelCapability.TEXT_PDF in required_capabilities:
        return PdfConfig(engine=PdfEngine.PDF_TEXT)
    elif ModelCapability.NATIVE_PDF in required_capabilities:
        return PdfConfig(engine=PdfEngine.NATIVE)
    else:
        return PdfConfig.default()
