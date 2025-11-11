import asyncio
import traceback
from datetime import datetime, timezone

from app.db.task_repo import TaskRepo
from app.events.task_events import create_task_failed_event
from app.models.task.enums import TaskStatus
from app.models.task.work_queue import WorkItemType, WorkQueueItem
from app.services.sse_service import SseService
from app.services.task_decomposition_service import TaskDecompositionService
from app.services.task_step_execution_service import TaskStepExecutionService


class WorkQueueService:
    """Service to process work queue items (task decomposition and step execution)"""
    
    def __init__(
        self,
        task_repo: TaskRepo,
        sse_service: SseService,
        decomposition_service: TaskDecompositionService,
        step_execution_service: TaskStepExecutionService,
    ) -> None:
        self.task_repo = task_repo
        self.sse_service = sse_service
        self.decomposition_service = decomposition_service
        self.step_execution_service = step_execution_service
        self._queue: asyncio.Queue[WorkQueueItem] = asyncio.Queue()
        self._processing = False
        self._processing_task: asyncio.Task | None = None
    
    async def enqueue(self, item: WorkQueueItem) -> None:
        """Add a work item to the queue"""
        await self._queue.put(item)
    
    async def enqueue_many(self, items: list[WorkQueueItem]) -> None:
        """Add multiple work items to the queue"""
        for item in items:
            await self._queue.put(item)
    
    def queue_size(self) -> int:
        """Get the current size of the queue"""
        return self._queue.qsize()
    
    def start_processing(self) -> None:
        """Start processing work queue items in the background"""
        if self._processing:
            return
        
        self._processing = True
        self._processing_task = asyncio.create_task(self._process_queue_loop())
    
    async def stop_processing(self) -> None:
        """Stop processing work queue items"""
        if not self._processing or not self._processing_task:
            return
        
        self._processing = False
        self._processing_task.cancel()
        try:
            await self._processing_task
        except asyncio.CancelledError:
            pass  # Expected on cancellation
    
    async def _process_queue_loop(self) -> None:
        """Main loop to process queue items"""
        while self._processing:
            try:
                item = await self._queue.get()
                
                try:
                    next_items = []
                    
                    if item.item_type == WorkItemType.DECOMPOSE_TASK:
                        next_items = await self.decomposition_service.decompose_and_queue_task(
                            task_id=item.task_id,
                            user_id=item.user_id,
                            api_key=item.api_key,
                        )
                    elif item.item_type == WorkItemType.EXECUTE_STEP:
                        if item.step_id is None:
                            raise Exception("Step ID is required for execute_step work item")
                        
                        next_items = await self.step_execution_service.execute_step(
                            step_id=item.step_id,
                            task_id=item.task_id,
                            user_id=item.user_id,
                            api_key=item.api_key,
                        )
                    
                    if next_items:
                        await self.enqueue_many(next_items)
                
                except Exception as e:
                    print(f"Error processing work item {item.item_type}: {e}")
                    traceback.print_exc()

                    self.task_repo.update_task_final_status(
                        task_id=item.task_id,
                        status=TaskStatus.FAILED,
                        completed_at=datetime.now(timezone.utc),
                    )
                    
                    task = self.task_repo.get_task_by_id(item.task_id, item.user_id)
                    if task:
                        await self.sse_service.emit_event(
                            user_id=item.user_id,
                            event=create_task_failed_event(task, str(e)),
                        )
            
            except asyncio.CancelledError:
                print("Work queue processing loop cancelled.")
                break
            except Exception as e:
                print(f"Unexpected error in work queue processing: {e}")
                await asyncio.sleep(1)
