from dataclasses import dataclass
from uuid import uuid4

from app.db.database import Database, register_schema_sql
from app.models.task.enums import CostKind


@dataclass
class TaskCostTotals:
    """Aggregated cost totals for a task."""

    pre_request_estimated_usd: float
    post_request_estimated_usd: float
    or_usd: float
    planning_or_usd: float


@register_schema_sql
def _create_task_costs_table() -> str:
    return """
        CREATE TABLE IF NOT EXISTS task_costs (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            cost_usd REAL NOT NULL,
            kind TEXT NOT NULL
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

    def add_pre_request_cost_increment(self, task_id: str, cost_usd: float) -> None:
        """Add a pre-request estimated cost entry for a task"""
        self._add_cost_increment(task_id, cost_usd, CostKind.ESTIMATED_PRE_REQUEST)

    def add_post_request_cost_increment(self, task_id: str, cost_usd: float) -> None:
        """Add a post-request estimated cost entry for a task"""
        self._add_cost_increment(task_id, cost_usd, CostKind.ESTIMATED_POST_REQUEST)

    def add_openrouter_cost_increment(self, task_id: str, cost_usd: float) -> None:
        """Add an OpenRouter-reported cost entry for a step-execution call"""
        self._add_cost_increment(task_id, cost_usd, CostKind.OPENROUTER)

    def add_planning_cost_increment(self, task_id: str, cost_usd: float) -> None:
        """Add an OpenRouter-reported cost entry for a planning (decomposition/reevaluation) call"""
        self._add_cost_increment(task_id, cost_usd, CostKind.PLANNING_OPENROUTER)

    def _add_cost_increment(self, task_id: str, cost_usd: float, kind: CostKind) -> None:
        """Insert a single cost row for a task"""
        self.db.execute_update(
            "INSERT INTO task_costs (id, task_id, cost_usd, kind) VALUES (?, ?, ?, ?)",
            (str(uuid4()), task_id, cost_usd, kind.value),
        )

    def get_total_cost(self, task_id: str) -> TaskCostTotals:
        """Get the total costs for a task broken down by kind"""
        rows = self.db.execute_query(
            """
            SELECT
                SUM(CASE WHEN kind = ? THEN cost_usd ELSE 0 END) AS pre_request_total,
                SUM(CASE WHEN kind = ? THEN cost_usd ELSE 0 END) AS post_request_total,
                SUM(CASE WHEN kind = ? THEN cost_usd ELSE 0 END) AS or_total,
                SUM(CASE WHEN kind = ? THEN cost_usd ELSE 0 END) AS planning_or_total
            FROM task_costs
            WHERE task_id = ?
            """,
            (
                CostKind.ESTIMATED_PRE_REQUEST.value,
                CostKind.ESTIMATED_POST_REQUEST.value,
                CostKind.OPENROUTER.value,
                CostKind.PLANNING_OPENROUTER.value,
                task_id,
            ),
        )

        if not rows:
            return TaskCostTotals(
                pre_request_estimated_usd=0.0,
                post_request_estimated_usd=0.0,
                or_usd=0.0,
                planning_or_usd=0.0,
            )

        row = rows[0]
        return TaskCostTotals(
            pre_request_estimated_usd=float(row["pre_request_total"]) if row["pre_request_total"] is not None else 0.0,
            post_request_estimated_usd=float(row["post_request_total"]) if row["post_request_total"] is not None else 0.0,
            or_usd=float(row["or_total"]) if row["or_total"] is not None else 0.0,
            planning_or_usd=float(row["planning_or_total"]) if row["planning_or_total"] is not None else 0.0,
        )
