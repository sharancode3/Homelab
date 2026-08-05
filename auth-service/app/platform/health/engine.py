from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from app.platform.health.enums import HealthCategory, HealthSeverity, HealthState, HealthStatus
from app.platform.health.exceptions import HealthException, HealthRequestError
from app.platform.health.models import HealthIndicator, HealthSnapshot
from app.platform.lifecycle import LifecycleManager
from app.platform.lifecycle.enums import LifecycleState
from app.project_registry import ProjectRegistryEntry
from app.project_registry_manager import ProjectRegistryManager


class HealthEngine:
    """Deterministic, read-only evaluation layer for project health."""

    def __init__(
        self,
        registry: ProjectRegistryManager,
        lifecycle_manager: LifecycleManager,
    ) -> None:
        self._registry = registry
        self._lifecycle_manager = lifecycle_manager

    def evaluate(self, project_id: str) -> HealthSnapshot:
        evaluated_at = datetime.now(timezone.utc)
        project = None

        try:
            if not project_id.strip():
                raise HealthRequestError("Project ID is required.")

            project = self._registry.get_by_project_id(project_id)
            if project is None:
                raise HealthRequestError(f"Unknown project: {project_id}")

            current_state = self._resolve_state(project_id)
            if current_state is None:
                raise HealthRequestError(f"Project has no lifecycle state: {project_id}")

            # Collect health indicators (simulated)
            indicators = self._collect_indicators(project_id)
            
            # Aggregate health state
            aggregated_state = self._aggregate_state(indicators, current_state)

            return HealthSnapshot(
                project_id=project_id,
                project_slug=getattr(project, "project_slug", None),
                project_name=getattr(project, "project_name", None),
                state=aggregated_state,
                status=HealthStatus.COMPLETED,
                indicators=indicators,
                evaluated_at=evaluated_at,
                message="Health evaluation completed successfully.",
                success=True,
            )

        except HealthException as error:
            return HealthSnapshot(
                project_id=project_id,
                project_slug=getattr(project, "project_slug", None) if project else None,
                project_name=getattr(project, "project_name", None) if project else None,
                state=HealthState.UNKNOWN,
                status=HealthStatus.FAILED,
                indicators=(),
                evaluated_at=evaluated_at,
                message=str(error),
                success=False,
                failure_reason=str(error),
            )

    def _resolve_state(self, project_id: str) -> LifecycleState | None:
        state_map = getattr(self._lifecycle_manager, "_states", None)
        if isinstance(state_map, dict):
            return state_map.get(project_id)

        get_state = getattr(self._lifecycle_manager, "get_state", None)
        if callable(get_state):
            return get_state(project_id)

        return None

    def _collect_indicators(self, project_id: str) -> tuple[HealthIndicator, ...]:
        # This is a simulation of health indicator collection.
        # In a real system, this would call various internal APIs or metrics endpoints.
        return (
            HealthIndicator(
                indicator_id="db_conn_1",
                name="Database Connectivity",
                category=HealthCategory.DATABASE,
                state=HealthState.HEALTHY,
                severity=HealthSeverity.INFO,
                details={"latency_ms": 15},
                checked_at=datetime.now(timezone.utc),
            ),
        )

    def _aggregate_state(
        self, indicators: Sequence[HealthIndicator], current_state: LifecycleState
    ) -> HealthState:
        if not indicators:
            return HealthState.UNKNOWN

        has_unhealthy = any(ind.state is HealthState.UNHEALTHY for ind in indicators)
        has_degraded = any(ind.state is HealthState.DEGRADED for ind in indicators)

        if has_unhealthy:
            return HealthState.UNHEALTHY
        if has_degraded:
            return HealthState.DEGRADED

        return HealthState.HEALTHY
