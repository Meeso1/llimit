from app.db.task_repo import TaskRepo
from app.db.task_cost_repo import TaskCostRepo
from app.models.task.models import TaskWithCost


class TaskQueryService:
    """Service for querying tasks with cost information"""

    def __init__(self, task_repo: TaskRepo, cost_repo: TaskCostRepo) -> None:
        self.task_repo = task_repo
        self.cost_repo = cost_repo

    def get_task_by_id(self, task_id: str, user_id: str) -> TaskWithCost | None:
        """Get a task by ID with cost information"""
        task = self.task_repo.get_task_by_id(task_id, user_id)
        if task is None:
            return None

        total_cost = self.cost_repo.get_total_cost(task_id)
        return task.with_cost(total_cost)

    def list_tasks_by_user(self, user_id: str) -> list[TaskWithCost]:
        """List all tasks for a user with cost information"""
        tasks = self.task_repo.list_tasks_by_user(user_id)
        
        tasks_with_cost = []
        for task in tasks:
            total_cost = self.cost_repo.get_total_cost(task.id)
            tasks_with_cost.append(task.with_cost(total_cost))
        
        return tasks_with_cost
