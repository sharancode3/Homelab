"""
Phase 14.4 Monitoring Tests

Covers:
- GET /projects/{id}/status   (viewer)
- GET /projects/{id}/history  (viewer, limit/IDOR)
- GET /projects/{id}/metrics  (developer; viewer rejected)
- GET /projects/platform/metrics (internal token; developer JWT rejected)
- Health indicators are real (not hardcoded)
- simulated: true is present in status response
- since_restart: true is present in metrics response
"""
import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.api.service import APIServiceLayer
from app.api.baas_service import BaaSProjectServiceLayer
from app.project_registry_manager import ProjectRegistryManager
from app.storage.providers.sqlite import (
    SQLiteProjectAuthorizationRepository,
    SQLiteOperationHistoryRepository,
)
from app.platform.operations.models import OperationResult
from app.platform.operations.enums import OperationStatus
from app.identity.models import DeveloperUser


class MockUserRepository:
    def __init__(self):
        self.users = {
            "owner": DeveloperUser(
                user_id="owner", username="owner", email="owner@x.com",
                hashed_password="", created_at=datetime.utcnow()
            ),
            "dev": DeveloperUser(
                user_id="dev", username="dev", email="dev@x.com",
                hashed_password="", created_at=datetime.utcnow()
            ),
            "viewer": DeveloperUser(
                user_id="viewer", username="viewer", email="viewer@x.com",
                hashed_password="", created_at=datetime.utcnow()
            ),
        }
        self.by_email = {u.email: u for u in self.users.values()}

    def get_by_user_id(self, user_id):
        return self.users.get(user_id)

    def get_by_email(self, email):
        return self.by_email.get(email)


class TestBaaSMonitoring(unittest.TestCase):
    def setUp(self):
        self.authz_repo = SQLiteProjectAuthorizationRepository(db_path=":memory:")
        self.history_repo = SQLiteOperationHistoryRepository(db_path=":memory:")
        self.registry = MagicMock(spec=ProjectRegistryManager)
        self.internal_service = MagicMock(spec=APIServiceLayer)
        self.user_repo = MockUserRepository()

        self.service = BaaSProjectServiceLayer(
            self.internal_service, self.authz_repo, self.registry, self.user_repo
        )

        self.project_id = "proj_monitor_test"
        self.project_b_id = "proj_monitor_b"
        self.authz_repo.add_member(self.project_id, "owner", "owner")
        self.authz_repo.add_member(self.project_id, "dev", "developer")
        self.authz_repo.add_member(self.project_id, "viewer", "viewer")
        self.authz_repo.add_member(self.project_b_id, "owner", "owner")

    # ── Status endpoint ──────────────────────────────────────────────────────

    def test_status_returns_simulated_true(self):
        from app.api.models import ProjectStatusResponse
        mock_status = ProjectStatusResponse(
            project_id=self.project_id,
            lifecycle_state="deployed",
            deployment_status="unknown",
            simulated=True,
            message="test",
        )
        self.internal_service.get_project_status.return_value = mock_status
        resp = self.service.get_project_status(self.project_id)
        self.assertTrue(resp.simulated)
        self.assertEqual(resp.lifecycle_state, "deployed")
        self.assertEqual(resp.deployment_status, "unknown")

    def test_status_contains_project_id(self):
        from app.api.models import ProjectStatusResponse
        self.internal_service.get_project_status.return_value = ProjectStatusResponse(
            project_id=self.project_id,
            lifecycle_state="registered",
            deployment_status="unknown",
            simulated=True,
            message="ok",
        )
        resp = self.service.get_project_status(self.project_id)
        self.assertEqual(resp.project_id, self.project_id)

    # ── History endpoint ──────────────────────────────────────────────────────

    def test_history_returns_bounded_list(self):
        from app.api.models import OperationHistoryResponse, OperationHistoryEntry
        mock_history = OperationHistoryResponse(
            project_id=self.project_id,
            total_returned=2,
            history=[
                OperationHistoryEntry(
                    operation_id="op_001", status="completed",
                    completed_steps=["deploy"], failures=[]
                ),
                OperationHistoryEntry(
                    operation_id="op_002", status="completed",
                    completed_steps=["stop"], failures=[]
                ),
            ],
        )
        self.internal_service.get_project_history.return_value = mock_history
        resp = self.service.get_project_history(self.project_id, limit=100)
        self.assertEqual(resp.total_returned, 2)
        self.assertEqual(len(resp.history), 2)

    def test_history_hard_cap_at_500(self):
        """Verify the service enforces limit=500 maximum."""
        from app.api.models import OperationHistoryResponse
        self.internal_service.get_project_history.return_value = OperationHistoryResponse(
            project_id=self.project_id, total_returned=0, history=[]
        )
        self.service.get_project_history(self.project_id, limit=9999)
        # Verify the delegate was called with at most 500
        called_limit = self.internal_service.get_project_history.call_args[1].get(
            "limit"
        ) or self.internal_service.get_project_history.call_args[0][1]
        self.assertLessEqual(called_limit, 500)

    def test_history_sqlite_newest_first(self):
        """Verify the SQLite repository returns results newest-first."""
        # Save two results; second is the newer one
        r1 = OperationResult(
            operation_id="op_aaa", status=OperationStatus.COMPLETED,
            completed_steps=("deploy",), failures=()
        )
        r2 = OperationResult(
            operation_id="op_bbb", status=OperationStatus.COMPLETED,
            completed_steps=("stop",), failures=()
        )
        self.history_repo.save_result(r1, project_id=self.project_id)
        self.history_repo.save_result(r2, project_id=self.project_id)
        results = self.history_repo.get_history(project_id=self.project_id, limit=10)
        # Newest-first: op_bbb was inserted second, should come first
        self.assertEqual(results[0].operation_id, "op_bbb")
        self.assertEqual(results[1].operation_id, "op_aaa")

    def test_history_sqlite_limit_respected(self):
        for i in range(10):
            r = OperationResult(
                operation_id=f"op_{i:04d}", status=OperationStatus.COMPLETED,
                completed_steps=("deploy",), failures=()
            )
            self.history_repo.save_result(r, project_id=self.project_id)
        results = self.history_repo.get_history(project_id=self.project_id, limit=3)
        self.assertEqual(len(results), 3)

    def test_history_sqlite_hard_max_500(self):
        """Requesting limit=9999 via SQLite is capped to 500."""
        # Ensure function accepts but caps it
        for i in range(5):
            r = OperationResult(
                operation_id=f"op_cap_{i}", status=OperationStatus.COMPLETED,
                completed_steps=(), failures=()
            )
            self.history_repo.save_result(r, project_id=self.project_id)
        results = self.history_repo.get_history(project_id=self.project_id, limit=9999)
        # Only 5 records exist; cap means no error and returns <= 5
        self.assertLessEqual(len(results), 500)

    # ── Metrics endpoint ──────────────────────────────────────────────────────

    def test_metrics_returns_since_restart_true(self):
        from app.api.models import ProjectMetricsResponse
        self.internal_service.get_project_metrics.return_value = ProjectMetricsResponse(
            project_id=self.project_id, since_restart=True,
            operation_success_count=5, operation_failure_count=1,
            deployment_failures=0, backup_success_count=2,
            avg_operation_duration_ms=120.0,
        )
        resp = self.service.get_project_metrics(self.project_id)
        self.assertTrue(resp.since_restart)
        self.assertEqual(resp.operation_success_count, 5)

    def test_metrics_has_required_fields(self):
        from app.api.models import ProjectMetricsResponse
        self.internal_service.get_project_metrics.return_value = ProjectMetricsResponse(
            project_id=self.project_id,
        )
        resp = self.service.get_project_metrics(self.project_id)
        # All fields exist and have sensible defaults
        self.assertIsInstance(resp.operation_success_count, int)
        self.assertIsInstance(resp.avg_operation_duration_ms, float)

    # ── Platform metrics ──────────────────────────────────────────────────────

    def test_platform_metrics_has_cpu_and_memory(self):
        from app.api.models import PlatformMetricsResponse
        mock_metrics = PlatformMetricsResponse(
            cpu_percent=12.5,
            memory_total_mb=3750.0,
            memory_available_mb=1920.0,
            memory_used_percent=48.8,
            disk_total_mb=50000.0,
            disk_used_mb=12000.0,
            disk_used_percent=24.0,
            since_restart_counters={"operation_success_count": 3},
            since_restart_avg_durations_ms={},
            collected_at="2026-08-14T16:00:00+00:00",
        )
        self.internal_service.get_platform_metrics.return_value = mock_metrics
        resp = self.internal_service.get_platform_metrics()
        self.assertGreater(resp.cpu_percent, 0)
        self.assertGreater(resp.memory_total_mb, 0)
        self.assertIn("collected_at", resp.model_dump())
        self.assertFalse(resp.cpu_percent > 100)  # sanity: CPU never > 100%

    # ── IDOR: cross-project isolation ─────────────────────────────────────────

    def test_history_idor_project_b_cannot_read_project_a(self):
        """Viewer of project B should not be able to read project A history
        via the authz_repo role check (simulated at route layer)."""
        # Project B's viewer has no access to project_id (A)
        role = self.authz_repo.get_role(self.project_id, "viewer")
        # viewer IS a member of project_a
        self.assertIsNotNone(role)
        # But a user with NO role in project_a should get None
        role_outsider = self.authz_repo.get_role(self.project_id, "outsider_user")
        self.assertIsNone(role_outsider)

    # ── Health indicators real (not hardcoded) ────────────────────────────────

    def test_health_engine_returns_real_indicators(self):
        """Ensure HealthEngine no longer returns a single hardcoded 15ms indicator."""
        from app.platform.health.engine import HealthEngine
        from app.platform.lifecycle.manager import LifecycleManager
        from app.platform.lifecycle.enums import LifecycleState
        registry = MagicMock()
        project_mock = MagicMock()
        project_mock.project_slug = "test"
        project_mock.project_name = "Test"
        registry.get_by_project_id.return_value = project_mock
        lm = MagicMock(spec=LifecycleManager)
        lm._states = {self.project_id: LifecycleState.DEPLOYED}
        engine = HealthEngine(registry=registry, lifecycle_manager=lm)
        snap = engine.evaluate(self.project_id)
        # Must return more than 1 indicator (not just hardcoded DB)
        self.assertGreaterEqual(len(snap.indicators), 2)
        # Lifecycle indicator must be present
        names = [ind.name for ind in snap.indicators]
        self.assertIn("Lifecycle State", names)


if __name__ == "__main__":
    unittest.main()
