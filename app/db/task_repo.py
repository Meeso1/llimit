import json
from datetime import datetime
from uuid import uuid4

from app.db.database import Database, register_schema_sql
from app.models.task.enums import TaskStatus, StepStatus, StepType, ComplexityLevel, ModelCapability
from app.models.task.models import (
    Task,
    TaskStep,
    NormalTaskStep,
    ReevaluateTaskStep,
    TaskStepDefinition,
    NormalTaskStepDefinition,
    ReevaluateTaskStepDefinition,
)


@register_schema_sql
def _create_tasks_table() -> str:
    return """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            title TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            steps_generated INTEGER NOT NULL DEFAULT 0,
            output TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """


@register_schema_sql
def _create_task_steps_table() -> str:
    return """
        CREATE TABLE IF NOT EXISTS task_steps (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            step_number INTEGER NOT NULL,
            prompt TEXT NOT NULL,
            status TEXT NOT NULL,
            step_type TEXT NOT NULL DEFAULT 'normal',
            step_details TEXT NOT NULL,
            model_name TEXT,
            response_content TEXT,
            output TEXT,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """


@register_schema_sql
def _create_tasks_index() -> str:
    return """
        CREATE INDEX IF NOT EXISTS idx_tasks_user_id 
        ON tasks(user_id)
    """


@register_schema_sql
def _create_task_steps_index() -> str:
    return """
        CREATE INDEX IF NOT EXISTS idx_task_steps_task_id 
        ON task_steps(task_id)
    """


class TaskRepo:
    """Repository for task and task step data access"""
    
    def __init__(self, db: Database) -> None:
        self.db = db
    
    def create_task(
        self,
        task_id: str,
        user_id: str,
        prompt: str,
        created_at: datetime,
    ) -> Task:
        """Create a new task"""
        self.db.execute_update(
            """
            INSERT INTO tasks 
            (id, user_id, prompt, status, created_at, steps_generated)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                user_id,
                prompt,
                TaskStatus.DECOMPOSING.value,
                created_at.isoformat(),
                0,
            ),
        )
        
        return Task(
            id=task_id,
            user_id=user_id,
            prompt=prompt,
            title=None,
            status=TaskStatus.DECOMPOSING,
            created_at=created_at,
            completed_at=None,
            steps_generated=False,
            output=None,
        )
    
    def get_task_by_id(self, task_id: str, user_id: str) -> Task | None:
        """Get a task by ID for a specific user"""
        rows = self.db.execute_query(
            """
            SELECT id, user_id, prompt, title, status, created_at, completed_at, steps_generated, output
            FROM tasks
            WHERE id = ? AND user_id = ?
            """,
            (task_id, user_id),
        )
        
        if not rows:
            return None
        
        return self._row_to_task(rows[0])
    
    def list_tasks_by_user(self, user_id: str) -> list[Task]:
        """List all tasks for a specific user"""
        rows = self.db.execute_query(
            """
            SELECT id, user_id, prompt, title, status, created_at, completed_at, steps_generated, output
            FROM tasks
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        
        return [self._row_to_task(row) for row in rows]
    
    def update_task_after_steps_generation(
        self,
        task_id: str,
        title: str,
        steps: list[TaskStepDefinition],
    ) -> Task | None:
        self.db.execute_update(
            """
            UPDATE tasks 
            SET title = ?, status = ?, steps_generated = ?
            WHERE id = ?
            """,
            (title, TaskStatus.IN_PROGRESS.value, 1, task_id),
        )
        
        for step_number, step_def in enumerate(steps):
            step_details = self._serialize_step_details(step_def)
            self.db.execute_update(
                """
                INSERT INTO task_steps 
                (id, task_id, step_number, prompt, status, step_type, step_details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    task_id,
                    step_number,
                    step_def.prompt,
                    StepStatus.PENDING.value,
                    step_def.step_type.value,
                    step_details,
                ),
            )
        
        rows = self.db.execute_query(
            "SELECT id, user_id, prompt, title, status, created_at, completed_at, steps_generated, output FROM tasks WHERE id = ?",
            (task_id,),
        )
        return self._row_to_task(rows[0]) if rows else None
    
    def update_task_final_status(
        self,
        task_id: str,
        status: TaskStatus,
        completed_at: datetime,
        output: str | None = None,
    ) -> Task | None:
        self.db.execute_update(
            "UPDATE tasks SET status = ?, completed_at = ?, output = ? WHERE id = ?",
            (status.value, completed_at.isoformat(), output, task_id),
        )
        
        rows = self.db.execute_query(
            "SELECT id, user_id, prompt, title, status, created_at, completed_at, steps_generated, output FROM tasks WHERE id = ?",
            (task_id,),
        )
        return self._row_to_task(rows[0]) if rows else None
    
    def get_steps_by_task_id(self, task_id: str, user_id: str, exclude_abandoned: bool = True) -> list[TaskStep] | None:
        task = self.get_task_by_id(task_id, user_id)
        if not task:
            return None
        
        query = """
            SELECT id, task_id, step_number, prompt, status, step_type, step_details,
                   model_name, response_content, output, started_at, completed_at
            FROM task_steps
            WHERE task_id = ?
        """
        
        if exclude_abandoned:
            query += " AND status != ?"
            params = (task_id, StepStatus.ABANDONED.value)
        else:
            params = (task_id,)
        
        query += " ORDER BY step_number ASC"
        
        rows = self.db.execute_query(query, params)
        
        return [self._row_to_task_step(row) for row in rows]
    
    def update_task_step(
        self,
        step_id: str,
        status: StepStatus | None = None,
        model_name: str | None = None,
        response_content: str | None = None,
        output: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> TaskStep | None:
        updates = []
        params = []
        
        if status is not None:
            updates.append("status = ?")
            params.append(status.value)
        
        if model_name is not None:
            updates.append("model_name = ?")
            params.append(model_name)
        
        if response_content is not None:
            updates.append("response_content = ?")
            params.append(response_content)
        
        if output is not None:
            updates.append("output = ?")
            params.append(output)
        
        if started_at is not None:
            updates.append("started_at = ?")
            params.append(started_at.isoformat())
        
        if completed_at is not None:
            updates.append("completed_at = ?")
            params.append(completed_at.isoformat())
        
        if not updates:
            rows = self.db.execute_query(
                """SELECT id, task_id, step_number, prompt, status, step_type, step_details,
                          model_name, response_content, output, started_at, completed_at
                   FROM task_steps WHERE id = ?""",
                (step_id,),
            )
            return self._row_to_task_step(rows[0]) if rows else None
        
        params.append(step_id)
        
        self.db.execute_update(
            f"UPDATE task_steps SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        
        rows = self.db.execute_query(
            """SELECT id, task_id, step_number, prompt, status, step_type, step_details,
                      model_name, response_content, output, started_at, completed_at
               FROM task_steps WHERE id = ?""",
            (step_id,),
        )
        return self._row_to_task_step(rows[0]) if rows else None
    
    def _row_to_task(self, row: dict) -> Task:
        return Task(
            id=row["id"],
            user_id=row["user_id"],
            prompt=row["prompt"],
            title=row["title"],
            status=TaskStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            steps_generated=bool(row["steps_generated"]),
            output=row["output"],
        )
    
    def get_step_by_id(self, step_id: str) -> TaskStep | None:
        """Get a step by its ID"""
        rows = self.db.execute_query(
            """
            SELECT id, task_id, step_number, prompt, status, step_type, step_details,
                   model_name, response_content, output, started_at, completed_at
            FROM task_steps
            WHERE id = ?
            """,
            (step_id,),
        )
        
        if not rows:
            return None
        
        return self._row_to_task_step(rows[0])
    
    def _row_to_task_step(self, row: dict) -> TaskStep:
        step_type = StepType(row["step_type"])
        step_details = json.loads(row["step_details"])
        
        common_fields = {
            "id": row["id"],
            "task_id": row["task_id"],
            "step_number": row["step_number"],
            "prompt": row["prompt"],
            "status": StepStatus(row["status"]),
            "step_type": step_type,
            "response_content": row["response_content"],
            "started_at": datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            "completed_at": datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        }
        
        if step_type == StepType.NORMAL:
            capabilities = [ModelCapability(cap) for cap in step_details["required_capabilities"]]
            return NormalTaskStep(
                **common_fields,
                complexity=ComplexityLevel(step_details["complexity"]),
                required_capabilities=capabilities,
                model_name=row["model_name"],
                output=row["output"],
            )
        elif step_type == StepType.REEVALUATE:
            return ReevaluateTaskStep(**common_fields)
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    def mark_steps_as_abandoned_after(self, task_id: str, after_step_number: int) -> None:
        """Mark all steps after a given step number as abandoned"""
        self.db.execute_update(
            """
            UPDATE task_steps
            SET status = ?
            WHERE task_id = ? AND step_number > ?
            """,
            (StepStatus.ABANDONED.value, task_id, after_step_number),
        )
    
    def insert_new_steps_after_reevaluation(
        self,
        task_id: str,
        after_step_number: int,
        new_steps: list[TaskStepDefinition],
    ) -> list[TaskStep]:
        """Insert new steps after a reevaluation step, returns the newly created steps"""
        created_steps = []
        
        for i, step_def in enumerate(new_steps):
            step_number = after_step_number + 1 + i
            step_details = self._serialize_step_details(step_def)
            step_id = str(uuid4())
            
            self.db.execute_update(
                """
                INSERT INTO task_steps 
                (id, task_id, step_number, prompt, status, step_type, step_details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step_id,
                    task_id,
                    step_number,
                    step_def.prompt,
                    StepStatus.PENDING.value,
                    step_def.step_type.value,
                    step_details,
                ),
            )
            
            step = self.get_step_by_id(step_id)
            if step:
                created_steps.append(step)
        
        return created_steps
    
    def _serialize_step_details(self, step_def: TaskStepDefinition) -> str:
        """Serialize type-specific step details to JSON"""
        if isinstance(step_def, NormalTaskStepDefinition):
            return json.dumps({
                "complexity": step_def.complexity.value,
                "required_capabilities": [cap.value for cap in step_def.required_capabilities],
            })
        elif isinstance(step_def, ReevaluateTaskStepDefinition):
            return json.dumps({})
        else:
            raise ValueError(f"Unknown step definition type: {type(step_def)}")
