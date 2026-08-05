import unittest
from typing import Any

from app.adapters.exceptions import (
    DeploymentAdapterError,
    EventTransportAdapterError,
    StorageAdapterError,
)
from app.adapters.interfaces import (
    DeploymentAdapter,
    EventTransportAdapter,
    StorageAdapter,
)


class MockStorageAdapter:
    def create_artifact(self, path: str, content: bytes) -> str:
        if not path:
            raise StorageAdapterError("Path is required")
        return f"ref_{path}"

    def read_artifact(self, reference: str) -> bytes:
        return b"content"

    def verify_artifact(self, reference: str) -> bool:
        return True

    def delete_artifact(self, reference: str) -> None:
        pass


class MockDeploymentAdapter:
    def prepare_deployment(self, project_id: str, configuration: dict[str, Any]) -> str:
        if not project_id:
            raise DeploymentAdapterError("Project ID required")
        return f"deploy_{project_id}"

    def execute_deployment(self, deployment_handle: str) -> bool:
        return True

    def check_status(self, deployment_handle: str) -> str:
        return "running"

    def rollback(self, deployment_handle: str) -> bool:
        return True


class MockEventTransportAdapter:
    def publish_event(self, topic: str, payload: bytes) -> str:
        if not topic:
            raise EventTransportAdapterError("Topic required")
        return f"msg_{topic}"

    def deliver_event(self, message_id: str, target: str) -> bool:
        return True

    def acknowledge_delivery(self, message_id: str, target: str) -> None:
        pass


class AdapterInterfacesTestCase(unittest.TestCase):
    def test_storage_adapter_protocol(self) -> None:
        adapter: StorageAdapter = MockStorageAdapter()
        
        ref = adapter.create_artifact("test.txt", b"data")
        self.assertEqual(ref, "ref_test.txt")
        
        data = adapter.read_artifact(ref)
        self.assertEqual(data, b"content")
        
        self.assertTrue(adapter.verify_artifact(ref))
        
        adapter.delete_artifact(ref)
        
        with self.assertRaises(StorageAdapterError):
            adapter.create_artifact("", b"")

    def test_deployment_adapter_protocol(self) -> None:
        adapter: DeploymentAdapter = MockDeploymentAdapter()
        
        handle = adapter.prepare_deployment("proj_1", {})
        self.assertEqual(handle, "deploy_proj_1")
        
        self.assertTrue(adapter.execute_deployment(handle))
        self.assertEqual(adapter.check_status(handle), "running")
        self.assertTrue(adapter.rollback(handle))
        
        with self.assertRaises(DeploymentAdapterError):
            adapter.prepare_deployment("", {})

    def test_event_transport_adapter_protocol(self) -> None:
        adapter: EventTransportAdapter = MockEventTransportAdapter()
        
        msg_id = adapter.publish_event("updates", b"event")
        self.assertEqual(msg_id, "msg_updates")
        
        self.assertTrue(adapter.deliver_event(msg_id, "consumer_1"))
        adapter.acknowledge_delivery(msg_id, "consumer_1")
        
        with self.assertRaises(EventTransportAdapterError):
            adapter.publish_event("", b"")


if __name__ == "__main__":
    unittest.main()
