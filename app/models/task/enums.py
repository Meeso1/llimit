from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    DECOMPOSING = "decomposing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"  # Failed due to exception/error
    COULD_NOT_COMPLETE = "could_not_complete"  # Failed due to model's inability to complete (non-exception)
    ABANDONED = "abandoned"


class StepType(str, Enum):
    NORMAL = "normal"
    REEVALUATE = "reevaluate"


class ComplexityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# TODO: Add PDF capabilities - native, PDF-text, mistral-OCR
class ModelCapability(str, Enum):
    REASONING = "reasoning"
    EXA_SEARCH = "exa_search"
    NATIVE_WEB_SEARCH = "native_web_search"
    OCR_PDF = "ocr_pdf_processing"
    TEXT_PDF = "text_pdf_processing"
    NATIVE_PDF = "native_pdf_processing"

    @staticmethod
    def descriptions() -> dict[str, str]:
        """Returns descriptions for each model capability."""
        return {
            ModelCapability.REASONING.value: "Internal reasoning/thinking generation before response",
            ModelCapability.EXA_SEARCH.value: "Web search based on prompt. Cheaper than native web search. It is run **BEFORE** LLM is called, and its result is provided to LLM as context.",
            ModelCapability.NATIVE_WEB_SEARCH.value: "Model-native web search. More expensive than exa search. It can be used by LLM with a generated query. Therefore, it can be used for more specific cases, where search query is different than the prompt.",
            ModelCapability.OCR_PDF.value: "OCR-based PDF processing via Mistral OCR. More expensive than text-based PDF processing. Can be used for image-based PDFs, like scanned documents.",
            ModelCapability.TEXT_PDF.value: "Text-based PDF processing. Cheaper than OCR-based PDF processing. Can be used for text-based PDFs, like reports, articles, papers. Images are still processed and attached as to model input.",
            ModelCapability.NATIVE_PDF.value: "Native PDF processing. More expensive than text-based PDF processing, and cheaper for weaker models (file will be processed as input tokens). Can be used for any PDFs. It's a good idea to use this instead of OCR-based processing if text processing is not enough, and the step only requires reading the PDF (no analysis, etc.)"
        }
