import json
import sqlite3
from datetime import datetime

from app.platform.audit.enums import AuditCategory, AuditSeverity, AuditStatus
from app.platform.audit.models import AuditRecord
from app.platform.operations.enums import OperationStatus
from app.platform.operations.models import OperationResult
from app.project_registry import ProjectRegistryEntry, ProjectStatus, ProjectType
from app.identity.models import DeveloperUser
from app.storage.exceptions import DuplicateRecordError, RecordNotFoundError
from app.storage.interfaces import (
    AuditRepository,
    OperationHistoryRepository,
    ProjectAuthorizationRepository,
    ProjectRepository,
    UserRepository,
)


class SQLiteProjectRepository(ProjectRepository):
    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                project_slug TEXT UNIQUE NOT NULL,
                project_type TEXT NOT NULL,
                status TEXT NOT NULL,
                project_version TEXT
            )
            """
        )
        self._conn.commit()

    def register(self, project: ProjectRegistryEntry) -> None:
        try:
            self._conn.execute(
                """
                INSERT INTO projects (
                    project_id, project_name, project_slug, project_type, status, project_version
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    project.project_id,
                    project.project_name,
                    project.project_slug,
                    project.project_type.value,
                    project.status.value,
                    getattr(project, "project_version", None),
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            self._conn.rollback()
            raise DuplicateRecordError(f"Project with ID {project.project_id} or slug {project.project_slug} already exists.")

    def get_by_project_id(self, project_id: str) -> ProjectRegistryEntry | None:
        row = self._conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        if not row:
            return None
        return self._row_to_entry(row)

    def get_by_project_slug(self, project_slug: str) -> ProjectRegistryEntry | None:
        row = self._conn.execute("SELECT * FROM projects WHERE project_slug = ?", (project_slug,)).fetchone()
        if not row:
            return None
        return self._row_to_entry(row)

    def get_all(self) -> tuple[ProjectRegistryEntry, ...]:
        rows = self._conn.execute("SELECT * FROM projects").fetchall()
        return tuple(self._row_to_entry(row) for row in rows)

    def _row_to_entry(self, row: sqlite3.Row) -> ProjectRegistryEntry:
        return ProjectRegistryEntry(
            project_id=row["project_id"],
            project_name=row["project_name"],
            project_slug=row["project_slug"],
            project_type=ProjectType(row["project_type"]),
            status=ProjectStatus(row["status"]),
            project_version=row["project_version"],
        )


class SQLiteAuditRepository(AuditRepository):
    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_records (
                audit_id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                source_component TEXT NOT NULL,
                target_identity TEXT,
                correlation_id TEXT,
                actor_context TEXT NOT NULL,
                outcome_status TEXT NOT NULL,
                summary TEXT NOT NULL,
                details TEXT NOT NULL,
                integrity_marker TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def append(self, record: AuditRecord) -> None:
        try:
            self._conn.execute(
                """
                INSERT INTO audit_records (
                    audit_id, version, timestamp, category, event_type, severity,
                    source_component, target_identity, correlation_id, actor_context,
                    outcome_status, summary, details, integrity_marker
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.audit_id,
                    record.version,
                    record.timestamp.isoformat(),
                    record.category.value,
                    record.event_type,
                    record.severity.value,
                    record.source_component,
                    record.target_identity,
                    record.correlation_id,
                    json.dumps(record.actor_context),
                    record.outcome_status.value,
                    record.summary,
                    json.dumps(record.details),
                    record.integrity_marker,
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            self._conn.rollback()
            raise DuplicateRecordError(f"Audit record {record.audit_id} already exists.")

    def query(
        self,
        project_id: str | None = None,
        category: AuditCategory | None = None,
        correlation_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[AuditRecord]:
        query = "SELECT * FROM audit_records WHERE 1=1"
        params = []

        if project_id is not None:
            query += " AND target_identity = ?"
            params.append(project_id)
        if category is not None:
            query += " AND category = ?"
            params.append(category.value)
        if correlation_id is not None:
            query += " AND correlation_id = ?"
            params.append(correlation_id)
        if start_time is not None:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        if end_time is not None:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> AuditRecord:
        return AuditRecord(
            audit_id=row["audit_id"],
            version=row["version"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            category=AuditCategory(row["category"]),
            event_type=row["event_type"],
            severity=AuditSeverity(row["severity"]),
            source_component=row["source_component"],
            target_identity=row["target_identity"],
            correlation_id=row["correlation_id"],
            actor_context=json.loads(row["actor_context"]),
            outcome_status=AuditStatus(row["outcome_status"]),
            summary=row["summary"],
            details=json.loads(row["details"]),
            integrity_marker=row["integrity_marker"],
        )


class SQLiteOperationHistoryRepository(OperationHistoryRepository):
    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_history (
                operation_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                completed_steps TEXT NOT NULL,
                failures TEXT NOT NULL,
                compensation_result TEXT NOT NULL,
                project_id TEXT,
                result TEXT DEFAULT '{}'
            )
            """
        )
        try:
            self._conn.execute("ALTER TABLE operation_history ADD COLUMN result TEXT DEFAULT '{}'")
        except sqlite3.OperationalError:
            pass
        # Add an index on project_id since we will query by it
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_op_project_id ON operation_history(project_id)"
        )
        self._conn.commit()

    def save_result(self, result: OperationResult, project_id: str | None = None) -> None:
        try:
            self._conn.execute(
                """
                INSERT INTO operation_history (
                    operation_id, status, completed_steps, failures, compensation_result, project_id, result
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.operation_id,
                    result.status.value,
                    json.dumps(result.completed_steps),
                    json.dumps(result.failures),
                    json.dumps(result.compensation_result),
                    project_id,
                    json.dumps(result.result),
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            self._conn.rollback()
            raise DuplicateRecordError(f"Operation {result.operation_id} already exists.")

    def get_history(
        self,
        project_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OperationResult]:
        # Enforce hard maximum to protect low-resource host
        limit = min(limit, 500)
        query = "SELECT * FROM operation_history"
        params: list = []
        if project_id is not None:
            query += " WHERE project_id = ?"
            params.append(project_id)
        # Newest-first ordering
        query += " ORDER BY rowid DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_result(row) for row in rows]

    def _row_to_result(self, row: sqlite3.Row) -> OperationResult:
        try:
            result_payload = json.loads(row["result"])
        except (KeyError, ValueError):
            result_payload = {}

        return OperationResult(
            operation_id=row["operation_id"],
            status=OperationStatus(row["status"]),
            completed_steps=tuple(json.loads(row["completed_steps"])),
            failures=tuple(json.loads(row["failures"])),
            compensation_result=json.loads(row["compensation_result"]),
            result=result_payload,
        )

class SQLiteUserRepository(UserRepository):
    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()

    def create(self, user: DeveloperUser) -> None:
        try:
            self._conn.execute(
                """
                INSERT INTO users (
                    user_id, username, email, hashed_password, created_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user.user_id,
                    user.username,
                    user.email,
                    user.hashed_password,
                    user.created_at.isoformat(),
                    1 if user.is_active else 0,
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            self._conn.rollback()
            raise DuplicateRecordError(f"User {user.email} or {user.username} already exists.")

    def get_by_user_id(self, user_id: str) -> DeveloperUser | None:
        row = self._conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return None
        return self._row_to_user(row)

    def get_by_username(self, username: str) -> DeveloperUser | None:
        row = self._conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            return None
        return self._row_to_user(row)

    def get_by_email(self, email: str) -> DeveloperUser | None:
        row = self._conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row:
            return None
        return self._row_to_user(row)

    def _row_to_user(self, row: sqlite3.Row) -> DeveloperUser:
        return DeveloperUser(
            user_id=row["user_id"],
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            created_at=datetime.fromisoformat(row["created_at"]),
            is_active=bool(row["is_active"]),
        )


class SQLiteProjectAuthorizationRepository(ProjectAuthorizationRepository):
    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS project_members (
                project_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                PRIMARY KEY (project_id, user_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_member_user_id ON project_members(user_id)"
        )
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS project_api_keys (
                key_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                secret_hash TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            )
        """)
        self._conn.commit()

    def add_member(self, project_id: str, user_id: str, role: str) -> None:
        try:
            self._conn.execute(
                """
                INSERT INTO project_members (project_id, user_id, role)
                VALUES (?, ?, ?)
                """,
                (project_id, user_id, role),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            self._conn.rollback()
            raise DuplicateRecordError(f"User {user_id} is already a member of {project_id}.")

    def get_projects_for_user(self, user_id: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT project_id FROM project_members WHERE user_id = ?",
            (user_id,)
        ).fetchall()
        return [row["project_id"] for row in rows]

    def check_access(self, project_id: str, user_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id)
        ).fetchone()
        return row is not None

    def get_role(self, project_id: str, user_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT role FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id)
        ).fetchone()
        return row["role"] if row else None

    def get_project_members(self, project_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT user_id, role FROM project_members WHERE project_id = ?",
            (project_id,)
        ).fetchall()
        return [{"user_id": row["user_id"], "role": row["role"]} for row in rows]

    def update_member_role(self, project_id: str, user_id: str, role: str) -> None:
        self._conn.execute(
            "UPDATE project_members SET role = ? WHERE project_id = ? AND user_id = ?",
            (role, project_id, user_id)
        )
        self._conn.commit()

    def remove_member(self, project_id: str, user_id: str) -> None:
        self._conn.execute(
            "DELETE FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id)
        )
        self._conn.commit()

    def count_owners(self, project_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) as c FROM project_members WHERE project_id = ? AND role = 'owner'",
            (project_id,)
        ).fetchone()
        return row["c"] if row else 0

    def create_api_key(self, key_id: str, project_id: str, name: str, secret_hash: str, created_by: str) -> None:
        self._conn.execute(
            """INSERT INTO project_api_keys
               (key_id, project_id, name, secret_hash, created_by, is_active)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (key_id, project_id, name, secret_hash, created_by)
        )
        self._conn.commit()

    def get_api_keys(self, project_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT key_id, name, created_at, is_active FROM project_api_keys WHERE project_id = ?",
            (project_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_api_key(self, key_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT key_id, project_id, name, secret_hash, is_active FROM project_api_keys WHERE key_id = ?",
            (key_id,)
        ).fetchone()
        return dict(row) if row else None

    def revoke_api_key(self, project_id: str, key_id: str) -> None:
        self._conn.execute(
            "UPDATE project_api_keys SET is_active = 0 WHERE project_id = ? AND key_id = ?",
            (project_id, key_id)
        )
        self._conn.commit()

class SQLiteRevocationRepository:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                jti TEXT PRIMARY KEY,
                expires_at TIMESTAMP NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON revoked_tokens(expires_at)")
        self._conn.commit()

    def revoke_token(self, jti: str, expires_at: datetime) -> None:
        import random
        self._conn.execute(
            "INSERT OR IGNORE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)",
            (jti, expires_at)
        )
        self._conn.commit()
        # Prune 5% of the time to keep storage bounded without heavy constant overhead
        if random.random() < 0.05:
            self.prune_expired()

    def is_token_revoked(self, jti: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM revoked_tokens WHERE jti = ?", (jti,)
        ).fetchone()
        return row is not None

    def prune_expired(self) -> None:
        self._conn.execute(
            "DELETE FROM revoked_tokens WHERE expires_at < ?",
            (datetime.utcnow(),)
        )
        self._conn.commit()
