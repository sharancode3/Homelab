from enum import Enum


class RestoreStatus(str, Enum):
    REQUESTED = "requested"
    VALIDATING = "validating"
    MANIFEST_VERIFIED = "manifest_verified"
    COMPATIBILITY_CHECKED = "compatibility_checked"
    PLANNED = "planned"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class RestoreType(str, Enum):
    FULL = "full"
    PARTIAL = "partial"


class RestoreMode(str, Enum):
    IN_PLACE = "in_place"
    NEW_PROJECT = "new_project"


class RestoreStage(str, Enum):
    REQUEST_VALIDATION = "request_validation"
    MANIFEST_VERIFICATION = "manifest_verification"
    COMPATIBILITY_CHECK = "compatibility_check"
    PLAN_CREATION = "plan_creation"
    EXECUTION_ORCHESTRATION = "execution_orchestration"
    RESTORE_VERIFICATION = "restore_verification"
    FINALIZATION = "finalization"
