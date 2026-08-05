class AdapterError(Exception):
    """Base exception for all adapter-related errors."""


class StorageAdapterError(AdapterError):
    """Raised when a storage adapter operation fails."""


class DeploymentAdapterError(AdapterError):
    """Raised when a deployment adapter operation fails."""


class EventTransportAdapterError(AdapterError):
    """Raised when an event transport adapter operation fails."""
