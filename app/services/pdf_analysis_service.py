from io import BytesIO
from dataclasses import dataclass

from pydantic import warnings
from pypdf import PdfReader

from app.services.tokenization_service import TokenizationService


@dataclass
class PdfAnalysisResult:
    """Result of PDF analysis"""
    page_count: int
    has_selectable_text: bool
    text_content: str
    text_token_count: int
    estimated_native_token_count: int


class PdfAnalysisService:
    """Service for analyzing PDF files"""

    def __init__(self, tokenization_service: TokenizationService) -> None:
        self._tokenization_service = tokenization_service

    def analyze_pdf(self, pdf_bytes: bytes) -> PdfAnalysisResult | None:
        """
        Analyze a PDF and extract information needed for LLM processing.
        
        Args:
            pdf_bytes: Raw PDF file bytes
            
        Returns:
            PdfAnalysisResult with page count, text content, and token estimates, or None if there was an error
        """
        # Create a BytesIO object from the bytes
        pdf_stream = BytesIO(pdf_bytes)
        
        try:
            reader = PdfReader(pdf_stream)
            page_count = len(reader.pages)
            text_content = self._extract_all_text(reader)
            
            # Check if PDF has selectable text
            # A PDF has selectable text if we extracted meaningful content
            # (more than just whitespace and a reasonable amount per page)
            has_selectable_text = len(text_content.strip()) > 50 and len(text_content) > (page_count * 20)
            
            # Count tokens in extracted text
            text_token_count = self._tokenization_service.count_tokens(text_content) if text_content else 0
            
            # Estimate native PDF token count
            # Native PDF processing typically includes:
            # - Text content
            # - Layout information
            # - Embedded images (if any)
            # - Structural metadata
            # Empirical estimates suggest native PDF processing uses 1.5-2.5x more tokens than pure text
            # We'll use 2x as a conservative estimate
            estimated_native_token_count = self._estimate_native_pdf_tokens(
                page_count=page_count,
                text_token_count=text_token_count,
                has_text=has_selectable_text
            )
            
            return PdfAnalysisResult(
                page_count=page_count,
                has_selectable_text=has_selectable_text,
                text_content=text_content,
                text_token_count=text_token_count,
                estimated_native_token_count=estimated_native_token_count
            )
            
        except Exception as e:
            warnings.warn(f"Failed to analyze PDF: {str(e)}")
            return None

    def _extract_all_text(self, reader: PdfReader) -> str:
        text_parts: list[str] = []
        for page in reader.pages:
            try:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            except Exception:
                # Skip pages that fail to extract
                continue
        
        text_content = "\n\n".join(text_parts)
        return text_content

    def _estimate_native_pdf_tokens(self, page_count: int, text_token_count: int, has_text: bool) -> int:
        """
        Estimate token count for native PDF processing.
        
        Native PDF processing includes layout, structure, and images in addition to text.
        This provides a rough estimate based on page count and text content.
        """
        if has_text and text_token_count > 0:
            # If PDF has text, estimate based on text tokens + overhead
            # Typical overhead is 1.5-2.5x for layout and structure
            base_estimate = int(text_token_count * 2.0)
            
            # Add tokens for images (rough estimate: ~500-1000 tokens per page for images)
            # We'll use a conservative estimate of 300 tokens per page for potential images
            image_overhead = page_count * 300
            
            return base_estimate + image_overhead
        else:
            # Image-only/scanned PDF - estimate based on page count
            # Typical estimate: 1500-3000 tokens per page for image-heavy PDFs
            # We'll use 2000 as a middle ground
            return page_count * 2000
