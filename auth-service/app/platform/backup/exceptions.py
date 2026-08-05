from typing import final


@final
class BackupException(Exception):
    """Base class for backup errors."""


@final
class BackupRequestError(BackupException):
    """Raised when the backup request is invalid."""


@final
class BackupPlanError(BackupException):
    """Raised when the backup plan is invalid."""


@final
class BackupManifestError(BackupException):
    """Raised when the backup manifest cannot be created or verified."""


@final
class BackupVerificationError(BackupException):
    """Raised when backup verification fails."""
