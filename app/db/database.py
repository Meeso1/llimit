import os
import sqlite3
from datetime import datetime
from typing import Any, Callable

from app.settings import settings


DB_VERSION = 3


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
    
    _schema_registry: list[str] = []
    
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path if db_path is not None else settings.db_path
        self._initialized = False
    
    def _initialize_schema(self) -> None:
        """Initialize database schema by executing all registered SQL
        
        This must be called before using the database. It executes all
        SQL statements that have been registered via register_schema().
        """
        if self._initialized:
            return
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            self._set_db_version(cursor)
            
            for sql in self._schema_registry:
                cursor.execute(sql)
            
            conn.commit()
        
        self._initialized = True

    def _set_db_version(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("CREATE TABLE IF NOT EXISTS db_version (version INTEGER NOT NULL)")
        cursor.execute("DELETE FROM db_version")
        cursor.execute("INSERT INTO db_version (version) VALUES (?)", (DB_VERSION,))
    
    def _get_db_version(self) -> int | None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='db_version'"
            )
            if cursor.fetchone() is None:
                return None
            
            cursor.execute("SELECT version FROM db_version LIMIT 1")
            result = cursor.fetchone()
            return result[0] if result else None
    
    def _handle_version_mismatch(self) -> None:
        """Handle database version mismatch by deleting or renaming the old db file"""
        if not os.path.exists(self.db_path):
            return
        
        if settings.preserve_old_db:
            self._backup_db()
        else:
            os.remove(self.db_path)
            print(f"Old database deleted: {self.db_path}")

    def _backup_db(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = self.db_path.replace(".db", f"-{timestamp}.db")
        if os.path.exists(backup_path):
            os.remove(self.db_path)
            print(f"Old database deleted - {backup_path} already exists")
        else:
            os.rename(self.db_path, backup_path)
            print(f"Old database renamed to: {backup_path}")
    
    def _check_and_handle_version(self) -> None:
        """Check database version and handle mismatch if necessary"""
        if not os.path.exists(self.db_path):
            return
        
        current_version = self._get_db_version()
        if current_version != DB_VERSION:
            print(f"Database is not up to date (db version: {current_version}, schema version: {DB_VERSION})")
            self._handle_version_mismatch()
    
    def setup(self) -> None:
        """Check database version and initialize schema"""
        self._check_and_handle_version()
        self._initialize_schema()
    
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
