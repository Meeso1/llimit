from dataclasses import dataclass
from enum import Enum


class PdfEngine(str, Enum):
    """PDF engine for PDF processing"""
    NATIVE = "native"
    MISTRAL_OCR = "mistral-ocr"
    PDF_TEXT = "pdf-text"


@dataclass
class PdfConfig:
    """Configuration for PDF processing in LLM completions"""
    engine: PdfEngine = PdfEngine.PDF_TEXT
    
    @classmethod
    def default(cls) -> "PdfConfig":
        """Create a default PDF config (text-based PDF processing)"""
        return cls(engine=PdfEngine.PDF_TEXT)
