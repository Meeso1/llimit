from pydantic import BaseModel, Field


class FileUploadMetadata(BaseModel):
    """Metadata accompanying a file upload"""
    filename: str = Field(..., description="Original filename")
    description: str | None = Field(None, description="Optional description of the file")
    content_type: str = Field(..., description="MIME type (e.g., image/jpeg, application/pdf, audio/wav, video/mp4)")


class FileUrlRequest(BaseModel):
    """Request to register a file URL"""
    url: str = Field(..., description="URL of the file (e.g., https://example.com/image.jpg)")
    filename: str = Field(..., description="Display filename for the URL")
    description: str | None = Field(None, description="Optional description of the file")
    content_type: str = Field(..., description="MIME type (e.g., image/jpeg, application/pdf, audio/wav, video/mp4)")

