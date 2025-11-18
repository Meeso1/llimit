from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import AuthContextDep, FileRepoDep, FileServiceDep
from app.models.file.responses import FileListResponse, FileMetadataResponse

router = APIRouter(
    prefix="/files",
    tags=["files"],
)


@router.post("", response_model=FileMetadataResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    content_type: str = Form(...),
    description: str | None = Form(None),
    context: AuthContextDep(require_openrouter_key=False) = None,
    file_service: FileServiceDep = None,
) -> FileMetadataResponse:
    """Upload a file"""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
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

