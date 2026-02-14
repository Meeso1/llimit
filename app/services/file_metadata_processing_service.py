from typing import Any

from app.services.pdf_analysis_service import PdfAnalysisService
from app.services.tokenization_service import TokenizationService


class FileMetadataProcessingService:
    """Service for processing file metadata and extracting additional information"""

    def __init__(
        self,
        pdf_analysis_service: PdfAnalysisService,
        tokenization_service: TokenizationService
    ) -> None:
        self._pdf_analysis_service = pdf_analysis_service
        self._tokenization_service = tokenization_service

    def process_file(
        self,
        content_type: str,
        file_content: bytes,
    ) -> dict[str, Any]:
        """
        Process a file and extract additional metadata.
        
        Args:
            content_type: MIME type of the file
            file_content: Raw file bytes
            
        Returns:
            Dictionary with additional metadata specific to the file type
        """
        if content_type == "application/pdf":
            return self._process_pdf(file_content)
        elif content_type.startswith("text/"):
            return self._process_text(file_content)
        
        return {}

    def _process_pdf(self, pdf_bytes: bytes) -> dict[str, Any]:
        """Process PDF and extract relevant metrics"""
        analysis = self._pdf_analysis_service.analyze_pdf(pdf_bytes)
        
        return {
            "page_count": analysis.page_count,
            "has_selectable_text": analysis.has_selectable_text,
            "text_token_count": analysis.text_token_count,
            "estimated_native_token_count": analysis.estimated_native_token_count,
        }

    def _process_text(self, text_bytes: bytes) -> dict[str, Any]:
        """Process text file and compute token count"""
        try:
            text_content = text_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Try with latin-1 as fallback
            text_content = text_bytes.decode("latin-1")
        
        token_count = self._tokenization_service.count_tokens(text_content)
        
        return {
            "token_count": token_count,
        }
