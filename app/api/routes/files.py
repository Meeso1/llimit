import json
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import AuthContextDep, FileRepoDep, FileServiceDep
from app.models.file.requests import FileUrlRequest
from app.models.file.responses import FileListResponse, FileMetadataResponse
from app.models.file.validation import AdditionalDataValidationError, validate_additional_data

router = APIRouter(
    prefix="/files",
    tags=["files"],
)


@router.post("", response_model=FileMetadataResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    content_type: str = Form(...),
    description: str | None = Form(None),
    additional_data: str | None = Form(None),
    context: AuthContextDep(require_openrouter_key=False) = None,
    file_service: FileServiceDep = None,
) -> FileMetadataResponse:
    """Upload a file"""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    
    # Parse and validate additional_data if provided
    parsed_additional_data: dict[str, Any] | None = None
    if additional_data:
        try:
            parsed_additional_data = json.loads(additional_data)
            if not isinstance(parsed_additional_data, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="additional_data must be a JSON object",
                )
            validate_additional_data(parsed_additional_data, content_type)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON in additional_data: {str(e)}",
            )
        except AdditionalDataValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    
    # Read file content
    file_content = await file.read()
    
    # Upload file
    file_metadata = await file_service.upload_file(
        user_id=context.user_id,
        filename=file.filename,
        description=description,
        content_type=content_type,
        file_content=file_content,
        user_additional_data=parsed_additional_data,
    )
    
    return file_metadata.to_response()


@router.post("/url", response_model=FileMetadataResponse, status_code=status.HTTP_201_CREATED)
async def register_file_url(
    request: FileUrlRequest,
    context: AuthContextDep(require_openrouter_key=False),
    file_service: FileServiceDep,
) -> FileMetadataResponse:
    """Register a file URL"""
    file_metadata = await file_service.register_file_url(
        user_id=context.user_id,
        url=request.url,
        filename=request.filename,
        description=request.description,
        content_type=request.content_type,
        user_additional_data=request.additional_data,
    )
    
    return file_metadata.to_response()


@router.get("", response_model=FileListResponse)
async def list_files(
    context: AuthContextDep(require_openrouter_key=False),
    file_repo: FileRepoDep,
) -> FileListResponse:
    """List all files for the current user"""
    files = file_repo.list_files_by_user(context.user_id)
    
    return FileListResponse(
        files=[f.to_response() for f in files],
    )

