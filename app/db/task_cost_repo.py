from uuid import uuid4

from app.db.database import Database, register_schema_sql


@register_schema_sql
def _create_task_costs_table() -> str:
    return """
        CREATE TABLE IF NOT EXISTS task_costs (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            cost_usd REAL NOT NULL
        )
    """


@register_schema_sql
def _create_task_costs_index() -> str:
    return """
        CREATE INDEX IF NOT EXISTS idx_task_costs_task_id 
        ON task_costs(task_id)
    """


class TaskCostRepo:
    """Repository for task cost data access"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def add_cost_increment(self, task_id: str, cost_usd: float) -> None:
        """Add a cost increment for a task"""
        self.db.execute_update(
            "INSERT INTO task_costs (id, task_id, cost_usd) VALUES (?, ?, ?)",
            (str(uuid4()), task_id, cost_usd),
        )

    def get_total_cost(self, task_id: str) -> float:
        """Get the total cost for a task"""
        rows = self.db.execute_query(
            "SELECT SUM(cost_usd) as total FROM task_costs WHERE task_id = ?",
            (task_id,),
        )

        if not rows or rows[0]["total"] is None:
            return 0.0

        return float(rows[0]["total"])
