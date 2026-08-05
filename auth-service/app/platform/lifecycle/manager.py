from datetime import datetime, timezone

from app.platform.lifecycle.enums import LifecycleOperation, LifecycleState
from app.platform.lifecycle.exceptions import (
    InvalidTransitionError,
    LifecycleConflictError,
    ProjectNotFoundError,
)
from app.platform.lifecycle.models import LifecycleResult
from app.project_registry import ProjectRegistryEntry
from app.project_registry_manager import ProjectRegistryManager


class LifecycleManager:
    """In-memory lifecycle coordinator for platform projects."""

    def __init__(self, registry: ProjectRegistryManager) -> None:
        self._registry = registry
        self._states: dict[str, LifecycleState] = {}

    def register(self, project_id: str) -> LifecycleResult:
        project = self._get_registry_project(project_id)

        if project_id in self._states:
            raise LifecycleConflictError(
                f"Project already registered with lifecycle manager: {project_id}"
            )

        previous_state = None
        current_state = LifecycleState.REGISTERED
        self._states[project_id] = current_state

        return self._result(
            project_id=project_id,
            project_slug=project.project_slug,
            project_name=project.project_name,
            operation=LifecycleOperation.REGISTER,
            previous_state=previous_state,
            current_state=current_state,
            message="Project registered for lifecycle management.",
        )

    def validate(self, project_id: str) -> LifecycleResult:
        return self._transition(
            project_id=project_id,
            operation=LifecycleOperation.VALIDATE,
            allowed_sources=(LifecycleState.REGISTERED,),
            target_state=LifecycleState.VALIDATED,
        )

    def deploy(self, project_id: str) -> LifecycleResult:
        return self._transition(
            project_id=project_id,
            operation=LifecycleOperation.DEPLOY,
            allowed_sources=(LifecycleState.VALIDATED,),
            target_state=LifecycleState.DEPLOYED,
        )

    def start(self, project_id: str) -> LifecycleResult:
        return self._transition(
            project_id=project_id,
            operation=LifecycleOperation.START,
            allowed_sources=(LifecycleState.DEPLOYED, LifecycleState.STOPPED),
            target_state=LifecycleState.RUNNING,
        )

    def stop(self, project_id: str) -> LifecycleResult:
        return self._transition(
            project_id=project_id,
            operation=LifecycleOperation.STOP,
            allowed_sources=(LifecycleState.RUNNING, LifecycleState.DEPLOYED),
            target_state=LifecycleState.STOPPED,
        )

    def archive(self, project_id: str) -> LifecycleResult:
        return self._transition(
            project_id=project_id,
            operation=LifecycleOperation.ARCHIVE,
            allowed_sources=(
                LifecycleState.RUNNING,
                LifecycleState.STOPPED,
                LifecycleState.FAILED,
            ),
            target_state=LifecycleState.ARCHIVED,
        )

    def fail(self, project_id: str, message: str | None = None) -> LifecycleResult:
        project = self._get_registry_project(project_id)
        current_state = self._get_current_state(project_id)

        if current_state is LifecycleState.FAILED:
            raise LifecycleConflictError(
                f"Project is already failed: {project_id}"
            )

        if current_state is LifecycleState.ARCHIVED:
            raise InvalidTransitionError(
                f"Cannot fail an archived project: {project_id}"
            )

        previous_state = current_state
        target_state = LifecycleState.FAILED
        self._states[project_id] = target_state

        return self._result(
            project_id=project_id,
            project_slug=project.project_slug,
            project_name=project.project_name,
            operation=LifecycleOperation.FAIL,
            previous_state=previous_state,
            current_state=target_state,
            message=message or "Project marked as failed.",
        )

    def _transition(
        self,
        project_id: str,
        operation: LifecycleOperation,
        allowed_sources: tuple[LifecycleState, ...],
        target_state: LifecycleState,
    ) -> LifecycleResult:
        project = self._get_registry_project(project_id)
        current_state = self._get_current_state(project_id)

        if current_state is target_state:
            raise LifecycleConflictError(
                f"Project is already in state {target_state.value}: {project_id}"
            )

        if current_state not in allowed_sources:
            raise InvalidTransitionError(
                f"Cannot transition project {project_id} from {current_state.value} to {target_state.value}"
            )

        previous_state = current_state
        self._states[project_id] = target_state

        return self._result(
            project_id=project_id,
            project_slug=project.project_slug,
            project_name=project.project_name,
            operation=operation,
            previous_state=previous_state,
            current_state=target_state,
            message=(
                f"Project transitioned from {previous_state.value} to {target_state.value}."
            ),
        )

    def _get_registry_project(self, project_id: str) -> ProjectRegistryEntry:
        project = self._registry.get_by_project_id(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Unknown project: {project_id}")

        return project

    def _get_current_state(self, project_id: str) -> LifecycleState:
        current_state = self._states.get(project_id)
        if current_state is None:
            raise LifecycleConflictError(
                f"Project has not been registered with lifecycle manager: {project_id}"
            )

        return current_state

    def _result(
        self,
        *,
        project_id: str,
        project_slug: str,
        project_name: str,
        operation: LifecycleOperation,
        previous_state: LifecycleState | None,
        current_state: LifecycleState,
        message: str,
    ) -> LifecycleResult:
        return LifecycleResult(
            project_id=project_id,
            project_slug=project_slug,
            project_name=project_name,
            operation=operation,
            previous_state=previous_state,
            current_state=current_state,
            success=True,
            changed=previous_state is not current_state,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )
