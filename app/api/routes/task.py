from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import AuthContextDep, TaskServiceDep
from app.models.task.requests import CreateTaskRequest
from app.models.task.responses import (
    TaskResponse,
    TaskListResponse,
    TaskStepListResponse,
)

router = APIRouter(
    prefix="/task",
    tags=["task"],
)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request_body: CreateTaskRequest,
    context: AuthContextDep(require_openrouter_key=True),
    task_service: TaskServiceDep,
) -> TaskResponse:
    """
    Create a new multi-step task.
    
    The task will be decomposed into steps asynchronously.
    Subscribe to SSE events to get notified when steps are generated and completed.
    """
    task = await task_service.create_task(
        user_id=context.user_id,
        request=request_body,
        api_key=context.openrouter_api_key,
    )
    return task.to_response()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    context: AuthContextDep(require_openrouter_key=False),
    task_service: TaskServiceDep,
) -> TaskListResponse:
    """Get all tasks for the current user"""
    tasks = await task_service.list_tasks(context.user_id)
    return TaskListResponse(
        tasks=[task.to_response() for task in tasks],
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    context: AuthContextDep(require_openrouter_key=False),
    task_service: TaskServiceDep,
) -> TaskResponse:
    """
    Get a specific task by ID.
    
    Returns the task state including:
    - Original prompt
    - Generated title (if steps have been generated)
    - Creation and completion times
    - Whether steps have been generated
    """
    task = await task_service.get_task(task_id, context.user_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task.to_response()


@router.get("/{task_id}/steps", response_model=TaskStepListResponse)
async def get_task_steps(
    task_id: str,
    context: AuthContextDep(require_openrouter_key=False),
    task_service: TaskServiceDep,
) -> TaskStepListResponse:
    """
    Get all steps for a specific task.
    
    Returns detailed information about each step including:
    - Step prompt
    - Current status
    - Selected model
    - Generated response (if completed)
    - Start and completion times
    - Dependencies on other steps
    """
    steps = await task_service.get_task_steps(task_id, context.user_id)
    if steps is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return TaskStepListResponse(
        task_id=task_id,
        steps=[step.to_response() for step in steps],
    )

