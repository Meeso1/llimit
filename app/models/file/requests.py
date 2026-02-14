from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.models.file.validation import validate_additional_data


class FileUploadMetadata(BaseModel):
    """Metadata accompanying a file upload"""
    filename: str = Field(..., description="Original filename")
    description: str | None = Field(None, description="Optional description of the file")
    content_type: str = Field(..., description="MIME type (e.g., image/jpeg, application/pdf, audio/wav, video/mp4)")
    additional_data: dict[str, Any] | None = Field(
        None,
        description="Optional additional metadata (e.g., page_count, token_count). Will be merged with auto-inferred data."
    )
    
    @field_validator("additional_data")
    @classmethod
    def validate_additional_data_field(cls, v: dict[str, Any] | None, info: ValidationInfo) -> dict[str, Any] | None:
        """Validate additional_data has correct types for known fields"""
        if v is None:
            return v
        
        # Get content_type from the model data
        content_type = info.data.get("content_type", "")
        validate_additional_data(v, content_type)
        return v


class FileUrlRequest(BaseModel):
    """Request to register a file URL"""
    url: str = Field(..., description="URL of the file (e.g., https://example.com/image.jpg)")
    filename: str = Field(..., description="Display filename for the URL")
    description: str | None = Field(None, description="Optional description of the file")
    content_type: str = Field(..., description="MIME type (e.g., image/jpeg, application/pdf, audio/wav, video/mp4)")
    additional_data: dict[str, Any] | None = Field(
        None,
        description="Optional additional metadata (e.g., page_count, token_count). Will be merged with auto-inferred data."
    )
    
    @field_validator("additional_data")
    @classmethod
    def validate_additional_data_field(cls, v: dict[str, Any] | None, info: ValidationInfo) -> dict[str, Any] | None:
        """Validate additional_data has correct types for known fields"""
        if v is None:
            return v
        
        # Get content_type from the model data
        content_type = info.data.get("content_type", "")
        validate_additional_data(v, content_type)
        return v

