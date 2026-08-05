from app.adapters.exceptions import StorageAdapterError


class LocalStorageError(StorageAdapterError):
    """Base exception for local storage provider errors."""


class ArtifactNotFoundError(LocalStorageError):
    """Raised when an artifact cannot be found in the local filesystem."""


class ArtifactIntegrityError(LocalStorageError):
    """Raised when an artifact checksum verification fails."""


class ArtifactWriteError(LocalStorageError):
    """Raised when an artifact cannot be written to disk."""
