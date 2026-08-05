class StorageError(Exception):
    """Base exception for all storage-related errors."""


class DuplicateRecordError(StorageError):
    """Raised when attempting to insert a record that already exists."""


class RecordNotFoundError(StorageError):
    """Raised when a requested record is not found."""
