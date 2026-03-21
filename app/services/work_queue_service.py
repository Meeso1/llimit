import asyncio
import logging
from datetime import datetime, timezone

from app.db.task_repo import TaskRepo
from app.events.task_events import create_task_failed_event
from app.models.task.enums import TaskStatus, WorkItemType
from app.models.task.work_queue import WorkQueueItem
from app.models.task.responses import StoppedTaskInfo
from app.services.sse_service import SseService
from app.services.task_decomposition_service import TaskDecompositionService
from app.services.task_step_execution_service import TaskStepExecutionService
from utils import not_none

logger = logging.getLogger(__name__)


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
        self._current_item: WorkQueueItem | None = None
        self._processing = False
        self._processing_task: asyncio.Task | None = None

    async def enqueue(self, item: WorkQueueItem) -> None:
        """Add a work item to the queue"""
        item.enqueue_time = datetime.now(timezone.utc)
        await self._queue.put(item)
        logger.info(
            "[task %s] Enqueued %s (step_number: %s, step: %s) — queue depth: %d items",
            item.task_id, item.item_type.value, item.step_number, item.step_id, self._queue.qsize(),
        )

    async def enqueue_many(self, items: list[WorkQueueItem]) -> None:
        """Add multiple work items to the queue"""
        for item in items:
            await self.enqueue(item)

    def queue_size(self) -> int:
        """Get the current size of the queue"""
        return self._queue.qsize()

    def get_pending_items(self) -> list[WorkQueueItem]:
        """Get a snapshot of items waiting in the queue (excludes the currently processing item)"""
        # asyncio.Queue does not expose contents for some reason
        return list(self._queue._queue)  # type: ignore[attr-defined]

    def get_current_item(self) -> WorkQueueItem | None:
        """Get the item currently being processed, if any"""
        return self._current_item

    def get_stopped_tasks(self) -> list[StoppedTaskInfo]:
        """Return tasks in active states that have no corresponding items in the queue"""
        active_tasks = self.task_repo.list_tasks_by_statuses(
            [TaskStatus.DECOMPOSING, TaskStatus.IN_PROGRESS]
        )
        queued_task_ids = {item.task_id for item in self.get_pending_items()}
        if self._current_item:
            queued_task_ids.add(self._current_item.task_id)
        return [
            StoppedTaskInfo(task_id=t.id, title=t.title, status=t.status)
            for t in active_tasks
            if t.id not in queued_task_ids
        ]

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
                item.start_time = datetime.now(timezone.utc)
                self._current_item = item

                logger.info(
                    "[task %s] Processing started: %s (step_number: %s, step: %s) — %d item(s) still pending",
                    item.task_id, item.item_type.value, item.step_number, item.step_id, self._queue.qsize(),
                )

                try:
                    next_items = []

                    if item.item_type == WorkItemType.DECOMPOSE_TASK:
                        next_items = await self.decomposition_service.decompose_and_queue_task(
                            task_id=item.task_id,
                            user_id=item.user_id,
                            api_key=item.api_key,
                        )
                    elif item.item_type == WorkItemType.EXECUTE_STEP:
                        next_items = await self.step_execution_service.execute_step(
                            step_id=not_none(item.step_id, "Step ID for execute_step work item"),
                            task_id=item.task_id,
                            user_id=item.user_id,
                            api_key=item.api_key,
                        )
                    elif item.item_type == WorkItemType.REEVALUATE:
                        next_items = await self.decomposition_service.reevaluate_and_queue_task(
                            step_id=not_none(item.step_id, "Step ID for reevaluate work item"),
                            task_id=item.task_id,
                            user_id=item.user_id,
                            api_key=item.api_key,
                        )

                    logger.info(
                        "[task %s] Processing completed: %s (step_number: %s, step: %s) — %d next item(s) queued",
                        item.task_id, item.item_type.value, item.step_number, item.step_id, len(next_items),
                    )

                    if next_items:
                        await self.enqueue_many(next_items)

                except Exception as e:
                    logger.error(
                        "[task %s] Error processing %s (step_number: %s, step: %s): %s",
                        item.task_id, item.item_type.value, item.step_number, item.step_id, e,
                        exc_info=True,
                    )

                    self.task_repo.update_task_final_status(
                        task_id=item.task_id,
                        status=TaskStatus.FAILED,
                        completed_at=datetime.now(timezone.utc),
                    )

                    task = not_none(self.task_repo.get_task_by_id(item.task_id, item.user_id), f"Task {item.task_id}")
                    await self.sse_service.emit_event(
                        user_id=item.user_id,
                        event=create_task_failed_event(task, str(e)),
                    )

                finally:
                    self._current_item = None

            except asyncio.CancelledError:
                logger.info("Work queue processing loop cancelled.")
                break
            except Exception as e:
                logger.error("Unexpected error in work queue processing: %s", e, exc_info=True)
                await asyncio.sleep(1)
