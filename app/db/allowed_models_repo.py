from app.db.database import Database, register_schema_sql


@register_schema_sql
def _create_allowed_models_table() -> str:
    return """
        CREATE TABLE IF NOT EXISTS allowed_models (
            model_id TEXT PRIMARY KEY
        )
    """


class AllowedModelsRepo:
    """Repository for the global list of allowed LLM models"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get_all(self) -> list[str]:
        """Return all allowed model IDs, or an empty list if none are set"""
        rows = self.db.execute_query("SELECT model_id FROM allowed_models")
        return [row["model_id"] for row in rows]

    def set_all(self, model_ids: list[str]) -> None:
        """Replace the entire allowed-models list atomically"""
        self.db._check_initialized()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM allowed_models")
            cursor.executemany(
                "INSERT INTO allowed_models (model_id) VALUES (?)",
                [(model_id,) for model_id in model_ids],
            )
            conn.commit()
