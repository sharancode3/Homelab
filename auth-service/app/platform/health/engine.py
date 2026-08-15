from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Sequence

from app.platform.health.enums import HealthCategory, HealthSeverity, HealthState, HealthStatus
from app.platform.health.exceptions import HealthException, HealthRequestError
from app.platform.health.models import HealthIndicator, HealthSnapshot
from app.platform.lifecycle import LifecycleManager
from app.platform.lifecycle.enums import LifecycleState
from app.project_registry_manager import ProjectRegistryManager


class HealthEngine:
    """Deterministic, read-only evaluation layer for project health."""

    def __init__(
        self,
        registry: ProjectRegistryManager,
        lifecycle_manager: LifecycleManager,
        tenant_db=None,
        storage_path: str | None = None,
    ) -> None:
        self._registry = registry
        self._lifecycle_manager = lifecycle_manager
        self._tenant_db = tenant_db
        self._storage_path = storage_path

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

            # Collect real health indicators
            indicators = self._collect_indicators(project_id, current_state)

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

    def _collect_indicators(
        self, project_id: str, current_state: LifecycleState
    ) -> tuple[HealthIndicator, ...]:
        indicators: list[HealthIndicator] = []
        now = datetime.now(timezone.utc)

        # 1. Database connectivity indicator — real SQLite latency probe
        db_indicator = self._check_database(project_id, now)
        indicators.append(db_indicator)

        # 2. Storage path indicator — check directory existence/writability
        storage_indicator = self._check_storage(project_id, now)
        indicators.append(storage_indicator)

        # 3. Lifecycle state indicator
        lifecycle_indicator = self._check_lifecycle(project_id, current_state, now)
        indicators.append(lifecycle_indicator)

        return tuple(indicators)

    def _check_database(self, project_id: str, now: datetime) -> HealthIndicator:
        """Real latency probe against the project's tenant SQLite database."""
        if self._tenant_db is None:
            return HealthIndicator(
                indicator_id=f"db_{project_id}",
                name="Database Connectivity",
                category=HealthCategory.DATABASE,
                state=HealthState.UNKNOWN,
                severity=HealthSeverity.WARNING,
                details={"reason": "tenant_db not configured"},
                checked_at=now,
            )

        try:
            start = time.perf_counter()
            conn = self._tenant_db.get_connection(project_id)
            conn.execute("SELECT 1").fetchone()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)

            if latency_ms > 500:
                state = HealthState.DEGRADED
                severity = HealthSeverity.WARNING
            else:
                state = HealthState.HEALTHY
                severity = HealthSeverity.INFO

            return HealthIndicator(
                indicator_id=f"db_{project_id}",
                name="Database Connectivity",
                category=HealthCategory.DATABASE,
                state=state,
                severity=severity,
                details={"latency_ms": latency_ms},
                checked_at=now,
            )
        except Exception as exc:
            return HealthIndicator(
                indicator_id=f"db_{project_id}",
                name="Database Connectivity",
                category=HealthCategory.DATABASE,
                state=HealthState.UNHEALTHY,
                severity=HealthSeverity.CRITICAL,
                details={"error": str(exc)},
                checked_at=now,
            )

    def _check_storage(self, project_id: str, now: datetime) -> HealthIndicator:
        """Verify the project's storage directory exists and is writable."""
        import os
        if self._storage_path is None:
            return HealthIndicator(
                indicator_id=f"storage_{project_id}",
                name="Storage Accessibility",
                category=HealthCategory.INFRASTRUCTURE,
                state=HealthState.UNKNOWN,
                severity=HealthSeverity.WARNING,
                details={"reason": "storage_path not configured"},
                checked_at=now,
            )

        project_storage = os.path.join(str(self._storage_path), project_id)
        exists = os.path.isdir(project_storage)
        writable = os.access(project_storage, os.W_OK) if exists else False

        import shutil
        if exists and writable:
            try:
                usage = shutil.disk_usage(project_storage)
                free_mb = usage.free / (1024 * 1024)
                if free_mb < 100:
                    state = HealthState.UNHEALTHY
                    severity = HealthSeverity.CRITICAL
                elif free_mb < 500:
                    state = HealthState.DEGRADED
                    severity = HealthSeverity.WARNING
                else:
                    state = HealthState.HEALTHY
                    severity = HealthSeverity.INFO
                details: dict = {"path": project_storage, "writable": True, "free_mb": round(free_mb, 2)}
            except Exception as e:
                state = HealthState.HEALTHY
                severity = HealthSeverity.INFO
                details: dict = {"path": project_storage, "writable": True, "error_checking_disk": str(e)}
        elif exists and not writable:
            state = HealthState.DEGRADED
            severity = HealthSeverity.WARNING
            details = {"path": project_storage, "writable": False}
        else:
            # Storage dir doesn't exist yet — not yet provisioned, not unhealthy
            state = HealthState.HEALTHY
            severity = HealthSeverity.INFO
            details = {"path": project_storage, "provisioned": False}

        return HealthIndicator(
            indicator_id=f"storage_{project_id}",
            name="Storage Accessibility",
            category=HealthCategory.INFRASTRUCTURE,
            state=state,
            severity=severity,
            details=details,
            checked_at=now,
        )

    def _check_lifecycle(
        self, project_id: str, current_state: LifecycleState, now: datetime
    ) -> HealthIndicator:
        """Surface the project's lifecycle state as a health indicator."""
        unhealthy_states = {LifecycleState.FAILED}
        degraded_states = {LifecycleState.STOPPED, LifecycleState.ARCHIVED}

        if current_state in unhealthy_states:
            state = HealthState.UNHEALTHY
            severity = HealthSeverity.CRITICAL
        elif current_state in degraded_states:
            state = HealthState.DEGRADED
            severity = HealthSeverity.WARNING
        else:
            state = HealthState.HEALTHY
            severity = HealthSeverity.INFO

        return HealthIndicator(
            indicator_id=f"lifecycle_{project_id}",
            name="Lifecycle State",
            category=HealthCategory.SYSTEM,
            state=state,
            severity=severity,
            details={"lifecycle_state": current_state.value},
            checked_at=now,
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
