from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timezone

from app.platform.deployment.enums import DeploymentStage, DeploymentStatus
from app.platform.deployment.exceptions import (
    DeploymentException,
    DeploymentPlanError,
    DeploymentRequestError,
    DeploymentVerificationError,
)
from app.platform.deployment.models import DeploymentPlan, DeploymentResult
from app.platform.lifecycle import LifecycleManager
from app.platform.lifecycle.enums import LifecycleOperation, LifecycleState
from app.platform.validation import ValidationEngine
from app.platform.validation.enums import ValidationStatus
from app.project_registry_manager import ProjectRegistryManager
from app.adapters.interfaces import DeploymentAdapter


class DeploymentEngine:
    """Deterministic deployment coordinator with no side effects."""

    def __init__(
        self,
        registry: ProjectRegistryManager,
        lifecycle_manager: LifecycleManager,
        validation_engine: ValidationEngine,
        deployment_adapter: DeploymentAdapter = None,
    ) -> None:
        self._registry = registry
        self._lifecycle_manager = lifecycle_manager
        self._validation_engine = validation_engine
        self._deployment_adapter = deployment_adapter
        self._deployment_handles: dict[str, str] = {}

    def create_plan(
        self,
        project_id: str,
        requested_by: str | None = None,
        timeout_seconds: int = 300,
        retry_count: int = 0,
        configuration: dict = None,
    ) -> DeploymentPlan:
        project = self._get_project(project_id)
        self._validate_request(project_id, timeout_seconds, retry_count)
        validation = self._validation_engine.validate(
            project_id, LifecycleOperation.DEPLOY
        )
        if validation.status is ValidationStatus.INVALID:
            raise DeploymentRequestError(
                f"Deployment request is invalid for project {project_id}."
            )

        return DeploymentPlan(
            project_id=project.project_id,
            project_slug=project.project_slug,
            project_name=project.project_name,
            requested_by=requested_by,
            status=DeploymentStatus.PLANNED,
            ordered_stages=self._default_stages(),
            dependencies=("validation", "lifecycle", "registry"),
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            verification_required=True,
            configuration=configuration or {},
            created_at=datetime.now(timezone.utc),
        )

    def deploy(
        self,
        project_id: str,
        requested_by: str | None = None,
        timeout_seconds: int = 300,
        retry_count: int = 0,
        configuration: dict = None,
    ) -> DeploymentResult:
        project = self._get_project(project_id)
        plan = self.create_plan(
            project_id=project_id,
            requested_by=requested_by,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            configuration=configuration,
        )

        started_at = datetime.now(timezone.utc)
        executed_stages: list[DeploymentStage] = []
        current_status = DeploymentStatus.VALIDATING

        try:
            self._execute_stage(DeploymentStage.REQUEST_VALIDATION, plan)
            executed_stages.append(DeploymentStage.REQUEST_VALIDATION)

            current_status = DeploymentStatus.EXECUTING
            self._execute_stage(DeploymentStage.PREPARATION, plan)
            executed_stages.append(DeploymentStage.PREPARATION)

            self._execute_stage(DeploymentStage.EXECUTION, plan)
            executed_stages.append(DeploymentStage.EXECUTION)

            current_status = DeploymentStatus.VERIFYING
            verification_passed = self._verify_deployment(plan, executed_stages)
            executed_stages.append(DeploymentStage.VERIFICATION)

            if not verification_passed:
                raise DeploymentVerificationError(
                    f"Deployment verification failed for {project_id}."
                )

            current_status = DeploymentStatus.COMPLETED
            executed_stages.append(DeploymentStage.FINALIZATION)

            return DeploymentResult(
                project_id=project.project_id,
                project_slug=project.project_slug,
                project_name=project.project_name,
                status=current_status,
                plan=plan,
                executed_stages=tuple(executed_stages),
                verification_passed=True,
                success=True,
                message="Deployment completed successfully.",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
        except DeploymentException as error:
            return DeploymentResult(
                project_id=project.project_id,
                project_slug=project.project_slug,
                project_name=project.project_name,
                status=DeploymentStatus.FAILED,
                plan=replace(plan, status=DeploymentStatus.FAILED),
                executed_stages=tuple(executed_stages),
                verification_passed=False,
                success=False,
                message=str(error),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                failure_reason=str(error),
            )

    def verify(self, plan: DeploymentPlan) -> bool:
        return bool(plan.ordered_stages) and plan.verification_required

    def _execute_stage(
        self, stage: DeploymentStage, plan: DeploymentPlan
    ) -> None:
        if stage not in plan.ordered_stages:
            raise DeploymentPlanError(
                f"Stage {stage.value} is not part of the deployment plan."
            )

        if not self._deployment_adapter:
            # If no adapter, fallback to no-op
            return

        try:
            if stage == DeploymentStage.PREPARATION:
                handle = self._deployment_adapter.prepare_deployment(plan.project_id, plan.configuration)
                self._deployment_handles[plan.project_id] = handle
            elif stage == DeploymentStage.EXECUTION:
                handle = self._deployment_handles.get(plan.project_id)
                if not handle:
                    raise DeploymentException("Cannot execute without a preparation handle.")
                self._deployment_adapter.execute_deployment(handle)
        except Exception as e:
            raise DeploymentException(f"Adapter error during {stage.value}: {e}") from e

    def _verify_deployment(
        self,
        plan: DeploymentPlan,
        executed_stages: Sequence[DeploymentStage],
    ) -> bool:
        return (
            DeploymentStage.REQUEST_VALIDATION in executed_stages
            and DeploymentStage.PREPARATION in executed_stages
            and DeploymentStage.EXECUTION in executed_stages
            and plan.verification_required
        )

    def _get_project(self, project_id: str):
        project = self._registry.get_by_project_id(project_id)
        if project is None:
            raise DeploymentRequestError(f"Unknown project: {project_id}")

        return project

    def _validate_request(
        self, project_id: str, timeout_seconds: int, retry_count: int
    ) -> None:
        if not project_id.strip():
            raise DeploymentRequestError("Project ID is required.")

        if timeout_seconds <= 0:
            raise DeploymentRequestError("Timeout must be positive.")

        if retry_count < 0:
            raise DeploymentRequestError("Retry count cannot be negative.")

        current_state = self._resolve_state(project_id)
        if current_state is None:
            raise DeploymentRequestError(
                f"Project is not registered with lifecycle manager: {project_id}"
            )

        if current_state not in (LifecycleState.VALIDATED, LifecycleState.DEPLOYED):
            raise DeploymentRequestError(
                f"Project {project_id} is not ready for deployment from state {current_state.value}."
            )

    def _resolve_state(self, project_id: str) -> LifecycleState | None:
        state_map = getattr(self._lifecycle_manager, "_states", None)
        if isinstance(state_map, dict):
            return state_map.get(project_id)

        get_state = getattr(self._lifecycle_manager, "get_state", None)
        if callable(get_state):
            return get_state(project_id)

        return None

    @staticmethod
    def _default_stages() -> tuple[DeploymentStage, ...]:
        return (
            DeploymentStage.REQUEST_VALIDATION,
            DeploymentStage.PREPARATION,
            DeploymentStage.EXECUTION,
            DeploymentStage.VERIFICATION,
            DeploymentStage.FINALIZATION,
        )
