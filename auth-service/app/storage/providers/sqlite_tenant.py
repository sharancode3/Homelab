import sqlite3
import re
import os
from contextlib import contextmanager
from typing import Iterator, List, Dict, Any
from pathlib import Path
from app.config import settings

# Validate table and column names to prevent SQL injection and enforce reserved namespaces
IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")

# Disallowed prefixes/names
RESERVED_PREFIXES = ("sqlite_", "_baas_")

class TenantDatabaseError(Exception):
    pass

class TenantDatabaseValidator:
    @staticmethod
    def validate_identifier(name: str) -> None:
        if not name:
            raise TenantDatabaseError("Identifier cannot be empty")
        if not IDENTIFIER_REGEX.match(name):
            raise TenantDatabaseError(f"Invalid identifier format: {name}")
        for prefix in RESERVED_PREFIXES:
            if name.lower().startswith(prefix):
                raise TenantDatabaseError(f"Identifier cannot use reserved prefix '{prefix}': {name}")

class SQLiteTenantConnectionFactory:
    """Manages secure, isolated connections to per-project SQLite databases."""
    
    def __init__(self, storage_path: str = None):
        self.base_dir = Path(storage_path or settings.storage_path)

    def _get_project_db_path(self, project_id: str) -> Path:
        if not project_id or not IDENTIFIER_REGEX.match(project_id.replace('-', '_')):
            # Ensure project_id itself doesn't contain path traversal characters
            raise TenantDatabaseError("Invalid project_id format")
        
        project_dir = self.base_dir / "projects" / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir / "data.db"

    @contextmanager
    def connect(self, project_id: str) -> Iterator[sqlite3.Connection]:
        db_path = self._get_project_db_path(project_id)
        
        # Simple lifecycle: open -> configure -> yield -> close
        conn = sqlite3.connect(
            str(db_path),
            timeout=5.0,  # 5000ms busy timeout
            isolation_level=None  # We manage transactions explicitly
        )
        conn.row_factory = sqlite3.Row
        
        try:
            # Enable WAL mode for concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            # Enforce foreign keys just in case
            conn.execute("PRAGMA foreign_keys=ON")
            # Begin our explicit transaction if we need one, but default to auto
            yield conn
        finally:
            conn.close()

class TenantDatabaseManager:
    """Provides Control Plane and Data Plane operations for a tenant database."""
    
    def __init__(self, factory: SQLiteTenantConnectionFactory):
        self.factory = factory
        self.MAX_TABLES = 50
        self.MAX_COLUMNS = 50

    # ================== CONTROL PLANE (TABLE MANAGEMENT) ==================

    def create_table(self, project_id: str, table_name: str, columns: Dict[str, str]) -> None:
        TenantDatabaseValidator.validate_identifier(table_name)
        
        if len(columns) > self.MAX_COLUMNS:
            raise TenantDatabaseError(f"Cannot exceed {self.MAX_COLUMNS} columns")
        if len(columns) == 0:
            raise TenantDatabaseError("Table must have at least one column")

        # Validate column names and types
        valid_types = {"TEXT", "INTEGER", "REAL", "JSON"}
        col_defs = []
        for col_name, col_type in columns.items():
            TenantDatabaseValidator.validate_identifier(col_name)
            col_type_upper = col_type.upper()
            if col_type_upper not in valid_types:
                raise TenantDatabaseError(f"Unsupported data type: {col_type}")
            
            # JSON is stored as TEXT in SQLite
            sqlite_type = "TEXT" if col_type_upper == "JSON" else col_type_upper
            col_defs.append(f'"{col_name}" {sqlite_type}')

        # Add default id column if not provided
        if "id" not in columns:
            col_defs.insert(0, '"id" TEXT PRIMARY KEY')

        columns_sql = ", ".join(col_defs)
        create_sql = f'CREATE TABLE "{table_name}" ({columns_sql});'

        with self.factory.connect(project_id) as conn:
            # Check table limit
            cursor = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            table_count = cursor.fetchone()[0]
            if table_count >= self.MAX_TABLES:
                raise TenantDatabaseError(f"Cannot exceed {self.MAX_TABLES} tables per project")

            try:
                conn.execute(create_sql)
            except sqlite3.OperationalError as e:
                if "already exists" in str(e):
                    raise TenantDatabaseError(f"Table {table_name} already exists")
                raise

    def list_tables(self, project_id: str) -> List[str]:
        with self.factory.connect(project_id) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            return [row["name"] for row in cursor.fetchall()]

    def get_table_schema(self, project_id: str, table_name: str) -> List[Dict[str, Any]]:
        TenantDatabaseValidator.validate_identifier(table_name)
        with self.factory.connect(project_id) as conn:
            # First check if table exists (to avoid error if it doesn't)
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                raise TenantDatabaseError(f"Table {table_name} does not exist")
                
            cursor = conn.execute(f'PRAGMA table_info("{table_name}")')
            return [dict(row) for row in cursor.fetchall()]

    def delete_table(self, project_id: str, table_name: str) -> None:
        TenantDatabaseValidator.validate_identifier(table_name)
        with self.factory.connect(project_id) as conn:
            try:
                conn.execute(f'DROP TABLE "{table_name}"')
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    raise TenantDatabaseError(f"Table {table_name} does not exist")
                raise

    def add_column(self, project_id: str, table_name: str, column_name: str, column_type: str) -> None:
        TenantDatabaseValidator.validate_identifier(table_name)
        TenantDatabaseValidator.validate_identifier(column_name)
        
        valid_types = {"TEXT", "INTEGER", "REAL", "JSON"}
        col_type_upper = column_type.upper()
        if col_type_upper not in valid_types:
            raise TenantDatabaseError(f"Unsupported data type: {column_type}")
        
        sqlite_type = "TEXT" if col_type_upper == "JSON" else col_type_upper
        
        with self.factory.connect(project_id) as conn:
            # Check table existence
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                raise TenantDatabaseError(f"Table {table_name} does not exist")
                
            # Check max columns
            cursor = conn.execute(f'PRAGMA table_info("{table_name}")')
            columns = cursor.fetchall()
            if len(columns) >= self.MAX_COLUMNS:
                raise TenantDatabaseError(f"Cannot exceed {self.MAX_COLUMNS} columns")
            
            # Check if column already exists
            for col in columns:
                if col["name"] == column_name:
                    raise TenantDatabaseError(f"Column {column_name} already exists in table {table_name}")

            try:
                conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {sqlite_type}')
            except sqlite3.Error as e:
                raise TenantDatabaseError(f"Database error: {str(e)}")

    # ================== DATA PLANE (ROW CRUD) ==================

    def insert_row(self, project_id: str, table_name: str, data: Dict[str, Any]) -> str:
        TenantDatabaseValidator.validate_identifier(table_name)
        if not data:
            raise TenantDatabaseError("Row data cannot be empty")

        columns = list(data.keys())
        for col in columns:
            TenantDatabaseValidator.validate_identifier(col)

        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join([f'"{c}"' for c in columns])
        values = tuple(data.values())

        sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

        with self.factory.connect(project_id) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.execute(sql, values)
                conn.execute("COMMIT")
                
                # Try to return the 'id' if provided, otherwise the rowid
                return str(data.get("id", cursor.lastrowid))
            except sqlite3.Error as e:
                conn.execute("ROLLBACK")
                raise TenantDatabaseError(f"Database error: {str(e)}")

    def get_row(self, project_id: str, table_name: str, row_id: str) -> Dict[str, Any]:
        TenantDatabaseValidator.validate_identifier(table_name)
        # Assuming table has 'id' column, otherwise fallback to rowid
        with self.factory.connect(project_id) as conn:
            try:
                # Try id first
                cursor = conn.execute(f'SELECT * FROM "{table_name}" WHERE id = ?', (row_id,))
                row = cursor.fetchone()
                if row: return dict(row)
            except sqlite3.OperationalError:
                # Fallback to rowid if 'id' doesn't exist
                try:
                    cursor = conn.execute(f'SELECT * FROM "{table_name}" WHERE rowid = ?', (row_id,))
                    row = cursor.fetchone()
                    if row: return dict(row)
                except sqlite3.OperationalError:
                    pass
        return None

    def list_rows(self, project_id: str, table_name: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        TenantDatabaseValidator.validate_identifier(table_name)
        # Hard limits
        limit = min(max(1, limit), 1000)
        offset = max(0, offset)

        with self.factory.connect(project_id) as conn:
            try:
                cursor = conn.execute(f'SELECT * FROM "{table_name}" LIMIT ? OFFSET ?', (limit, offset))
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    raise TenantDatabaseError(f"Table {table_name} does not exist")
                raise

    def update_row(self, project_id: str, table_name: str, row_id: str, data: Dict[str, Any]) -> bool:
        TenantDatabaseValidator.validate_identifier(table_name)
        if not data:
            return False

        columns = list(data.keys())
        for col in columns:
            TenantDatabaseValidator.validate_identifier(col)

        set_clause = ", ".join([f'"{c}" = ?' for c in columns])
        values = tuple(data.values()) + (row_id,)

        with self.factory.connect(project_id) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                # Try id first
                sql = f'UPDATE "{table_name}" SET {set_clause} WHERE id = ?'
                try:
                    cursor = conn.execute(sql, values)
                    if cursor.rowcount == 0:
                        # Fallback to rowid
                        sql = f'UPDATE "{table_name}" SET {set_clause} WHERE rowid = ?'
                        cursor = conn.execute(sql, values)
                    conn.execute("COMMIT")
                    return cursor.rowcount > 0
                except sqlite3.OperationalError:
                    # Fallback to rowid if id column missing
                    sql = f'UPDATE "{table_name}" SET {set_clause} WHERE rowid = ?'
                    cursor = conn.execute(sql, values)
                    conn.execute("COMMIT")
                    return cursor.rowcount > 0
            except sqlite3.Error as e:
                conn.execute("ROLLBACK")
                raise TenantDatabaseError(f"Database error: {str(e)}")

    def delete_row(self, project_id: str, table_name: str, row_id: str) -> bool:
        TenantDatabaseValidator.validate_identifier(table_name)
        with self.factory.connect(project_id) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    cursor = conn.execute(f'DELETE FROM "{table_name}" WHERE id = ?', (row_id,))
                    if cursor.rowcount == 0:
                        cursor = conn.execute(f'DELETE FROM "{table_name}" WHERE rowid = ?', (row_id,))
                except sqlite3.OperationalError:
                    cursor = conn.execute(f'DELETE FROM "{table_name}" WHERE rowid = ?', (row_id,))
                conn.execute("COMMIT")
                return cursor.rowcount > 0
            except sqlite3.Error as e:
                conn.execute("ROLLBACK")
                raise TenantDatabaseError(f"Database error: {str(e)}")
