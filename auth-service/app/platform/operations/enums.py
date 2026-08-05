from enum import Enum


class OperationType(str, Enum):
    DEPLOY = "deploy"
    STOP = "stop"
    RESTART = "restart"
    BACKUP = "backup"
    RESTORE = "restore"
    ARCHIVE = "archive"


class OperationStatus(str, Enum):
    REQUESTED = "requested"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
