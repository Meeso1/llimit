import io
import wave
from typing import Any

from mutagen.mp3 import MP3

from app.services.office_conversion_service import OfficeConversionService, XLSX_CONTENT_TYPE, DOCX_CONTENT_TYPE
from app.services.pdf_analysis_service import PdfAnalysisService
from app.services.tokenization_service import TokenizationService


class FileMetadataProcessingService:
    """Service for processing file metadata and extracting additional information"""

    def __init__(
        self,
        pdf_analysis_service: PdfAnalysisService,
        tokenization_service: TokenizationService,
        office_conversion_service: OfficeConversionService,
    ) -> None:
        self._pdf_analysis_service = pdf_analysis_service
        self._tokenization_service = tokenization_service
        self._office_conversion_service = office_conversion_service

    def process_file(
        self,
        content_type: str,
        file_content: bytes,
    ) -> dict[str, Any]:
        """Process a file and extract additional metadata."""
        if content_type == "application/pdf":
            return self._process_pdf(file_content)
        elif content_type.startswith("text/") or content_type == "application/json":
            return self._process_text(file_content)
        elif content_type in (XLSX_CONTENT_TYPE, DOCX_CONTENT_TYPE):
            text = self._office_conversion_service.extract_text(content_type, file_content)
            token_count = self._tokenization_service.count_tokens(text)
            return {"token_count": token_count}
        elif content_type.startswith("audio/"):
            return self._process_audio(content_type, file_content)

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

    def _process_audio(self, content_type: str, audio_bytes: bytes) -> dict[str, Any]:
        """Read audio duration from file headers without decoding audio data."""
        try:
            if content_type == "audio/wav":
                with wave.open(io.BytesIO(audio_bytes)) as wf:
                    length_seconds = wf.getnframes() / wf.getframerate()
            elif content_type in ("audio/mp3", "audio/mpeg"):
                audio = MP3(io.BytesIO(audio_bytes))
                length_seconds = audio.info.length
            else:
                raise ValueError(f"Unexpected audio content type: {content_type}")

            return {"length_seconds": length_seconds}
        except Exception:
            return {}

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
