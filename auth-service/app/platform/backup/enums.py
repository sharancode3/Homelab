from enum import Enum


class BackupStatus(str, Enum):
    REQUESTED = "requested"
    PLANNED = "planned"
    VALIDATING = "validating"
    MANIFEST_CREATED = "manifest_created"
    METADATA_GENERATED = "metadata_generated"
    ARTIFACT_SIMULATED = "artifact_simulated"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class BackupType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class BackupStage(str, Enum):
    PLAN_CREATION = "plan_creation"
    REQUEST_VALIDATION = "request_validation"
    MANIFEST_CREATION = "manifest_creation"
    METADATA_GENERATION = "metadata_generation"
    ARTIFACT_SIMULATION = "artifact_simulation"
    MANIFEST_VERIFICATION = "manifest_verification"
    FINALIZATION = "finalization"
