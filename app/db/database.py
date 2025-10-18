import sqlite3
from typing import Any, Callable


class DatabaseNotInitializedError(Exception):
    """Raised when database operations are attempted before initialization"""
    pass


def register_schema_sql(func: Callable[[], str]) -> Callable[[], str]:
    """Decorator to register SQL returned by a function for schema initialization
    
    This decorator should be used on functions that return SQL statements
    for table creation, indexes, etc. The function is called immediately
    and its return value is registered for execution during database initialization.
    
    Example:
        @register_schema_sql
        def _create_users_table() -> str:
            return "CREATE TABLE IF NOT EXISTS users (...)"
    """
    sql = func()
    Database._schema_registry.append(sql)
    return func


class Database:
    """SQLite database connection manager with schema registration"""
    
    # Class-level registry for schema initialization SQL
    _schema_registry: list[str] = []
    
    def __init__(self, db_path: str = "data/llimit.db") -> None:
        self.db_path = db_path
        self._initialized = False
    
    def initialize_schema(self) -> None:
        """Initialize database schema by executing all registered SQL
        
        This must be called before using the database. It executes all
        SQL statements that have been registered via register_schema().
        """
        if self._initialized:
            return
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for sql in self._schema_registry:
                cursor.execute(sql)
            
            conn.commit()
        
        self._initialized = True
    
    def _check_initialized(self) -> None:
        """Check if database has been initialized, raise error if not"""
        if not self._initialized:
            raise DatabaseNotInitializedError(
                "Database has not been initialized. Call initialize_schema() first."
            )
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn
    
    def execute_query(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Execute a SELECT query and return results"""
        self._check_initialized()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple[Any, ...] = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        self._check_initialized()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

