from pydantic import BaseModel, Field


class FileUploadMetadata(BaseModel):
    """Metadata accompanying a file upload"""
    filename: str = Field(..., description="Original filename")
    description: str | None = Field(None, description="Optional description of the file")
    content_type: str = Field(..., description="MIME type (e.g., image/jpeg, application/pdf, audio/wav, video/mp4)")

