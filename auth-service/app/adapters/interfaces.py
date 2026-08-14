from typing import Protocol, Any

class StorageAdapter(Protocol):
    """Interface for storage providers (e.g., S3, local disk)."""

    def create_artifact(self, path: str, content: bytes) -> str:
        """Create a storage artifact and return its reference URI/ID."""
        ...

    def create_artifact_stream(self, path: str, stream: Any) -> str:
        """Create a storage artifact from a binary stream (e.g., UploadFile.file) and return its reference URI/ID."""
        ...

    def read_artifact(self, reference: str) -> bytes:
        """Read an artifact from storage by its reference."""
        ...

    def read_artifact_stream(self, reference: str) -> Any:
        """Read an artifact from storage by its reference and return a binary stream/generator."""
        ...

    def verify_artifact(self, reference: str) -> bool:
        """Verify the integrity or existence of an artifact."""
        ...

    def delete_artifact(self, reference: str) -> None:
        """Delete an artifact from storage when allowed."""
        ...


class DeploymentAdapter(Protocol):
    """Interface for deployment providers (e.g., Kubernetes, Docker)."""

    def prepare_deployment(self, project_id: str, configuration: dict[str, Any]) -> str:
        """Prepare deployment and return a deployment handle/ID."""
        ...

    def execute_deployment(self, deployment_handle: str) -> bool:
        """Execute the prepared deployment action."""
        ...

    def check_status(self, deployment_handle: str) -> str:
        """Check the current status of a deployment."""
        ...

    def rollback(self, deployment_handle: str) -> bool:
        """Rollback a failed or active deployment."""
        ...


class EventTransportAdapter(Protocol):
    """Interface for event transport providers (e.g., Kafka, Redis PubSub)."""

    def publish_event(self, topic: str, payload: bytes) -> str:
        """Publish an event to a topic and return a message ID."""
        ...

    def deliver_event(self, message_id: str, target: str) -> bool:
        """Deliver a specific event to a target consumer."""
        ...

    def acknowledge_delivery(self, message_id: str, target: str) -> None:
        """Acknowledge successful delivery of an event."""
        ...
