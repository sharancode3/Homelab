import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from app.platform.health.engine import HealthEngine
from app.platform.health.enums import HealthState, HealthSeverity
from app.platform.lifecycle.enums import LifecycleState

class TestDiskHealth(unittest.TestCase):
    def setUp(self):
        self.engine = HealthEngine(None, None, None, "/tmp/fake_storage")

    @patch("os.path.isdir")
    @patch("os.access")
    @patch("shutil.disk_usage")
    def test_healthy_disk(self, mock_usage, mock_access, mock_isdir):
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_usage.return_value = MagicMock(free=1000 * 1024 * 1024) # 1000 MB

        indicator = self.engine._check_storage("proj_1", datetime.now(timezone.utc))
        self.assertEqual(indicator.state, HealthState.HEALTHY)
        self.assertEqual(indicator.severity, HealthSeverity.INFO)

    @patch("os.path.isdir")
    @patch("os.access")
    @patch("shutil.disk_usage")
    def test_degraded_disk(self, mock_usage, mock_access, mock_isdir):
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_usage.return_value = MagicMock(free=400 * 1024 * 1024) # 400 MB

        indicator = self.engine._check_storage("proj_1", datetime.now(timezone.utc))
        self.assertEqual(indicator.state, HealthState.DEGRADED)
        self.assertEqual(indicator.severity, HealthSeverity.WARNING)

    @patch("os.path.isdir")
    @patch("os.access")
    @patch("shutil.disk_usage")
    def test_critical_disk(self, mock_usage, mock_access, mock_isdir):
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_usage.return_value = MagicMock(free=50 * 1024 * 1024) # 50 MB

        indicator = self.engine._check_storage("proj_1", datetime.now(timezone.utc))
        self.assertEqual(indicator.state, HealthState.UNHEALTHY)
        self.assertEqual(indicator.severity, HealthSeverity.CRITICAL)

    @patch("os.path.isdir")
    @patch("os.access")
    def test_unwritable_disk(self, mock_access, mock_isdir):
        mock_isdir.return_value = True
        mock_access.return_value = False

        indicator = self.engine._check_storage("proj_1", datetime.now(timezone.utc))
        self.assertEqual(indicator.state, HealthState.DEGRADED)
        self.assertEqual(indicator.severity, HealthSeverity.WARNING)
