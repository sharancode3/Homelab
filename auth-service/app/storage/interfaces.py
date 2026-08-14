from __future__ import annotations
from typing import Protocol, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.project_registry import ProjectRegistryEntry
    from app.platform.audit.enums import AuditCategory
    from app.platform.audit.models import AuditRecord
    from app.platform.operations.models import OperationResult
    from app.identity.models import DeveloperUser

class ProjectRepository(Protocol):
    def register(self, project: ProjectRegistryEntry) -> None:
        ...

    def get_by_project_id(self, project_id: str) -> ProjectRegistryEntry | None:
        ...

    def get_by_project_slug(self, project_slug: str) -> ProjectRegistryEntry | None:
        ...

    def get_all(self) -> tuple[ProjectRegistryEntry, ...]:
        ...

class ProjectAuthorizationRepository(Protocol):
    def add_member(self, project_id: str, user_id: str, role: str) -> None:
        ...

    def get_projects_for_user(self, user_id: str) -> list[str]:
        ...

    def check_access(self, project_id: str, user_id: str) -> bool:
        ...

    def get_role(self, project_id: str, user_id: str) -> str | None:
        ...

    def get_project_members(self, project_id: str) -> list[dict]:
        ...

    def update_member_role(self, project_id: str, user_id: str, role: str) -> None:
        ...

    def remove_member(self, project_id: str, user_id: str) -> None:
        ...

    def count_owners(self, project_id: str) -> int:
        ...


class AuditRepository(Protocol):
    def append(self, record: AuditRecord) -> None:
        ...

    def query(
        self,
        project_id: str | None = None,
        category: AuditCategory | None = None,
        correlation_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[AuditRecord]:
        ...

class OperationHistoryRepository(Protocol):
    def save_result(self, result: OperationResult, project_id: str | None = None) -> None:
        ...

    def get_history(self, project_id: str | None = None) -> list[OperationResult]:
        ...

class UserRepository(Protocol):
    def create(self, user: DeveloperUser) -> None:
        ...

    def get_by_user_id(self, user_id: str) -> DeveloperUser | None:
        ...

    def get_by_username(self, username: str) -> DeveloperUser | None:
        ...

    def get_by_email(self, email: str) -> DeveloperUser | None:
        ...
