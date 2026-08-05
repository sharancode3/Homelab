from enum import Enum


class DeploymentStatus(str, Enum):
    REQUESTED = "requested"
    PLANNED = "planned"
    VALIDATING = "validating"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class DeploymentStage(str, Enum):
    PLAN_GENERATION = "plan_generation"
    REQUEST_VALIDATION = "request_validation"
    PREPARATION = "preparation"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    FINALIZATION = "finalization"
