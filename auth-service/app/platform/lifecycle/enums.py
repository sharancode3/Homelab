from enum import Enum


class LifecycleState(str, Enum):
    REGISTERED = "registered"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    ARCHIVED = "archived"


class LifecycleOperation(str, Enum):
    REGISTER = "register"
    VALIDATE = "validate"
    DEPLOY = "deploy"
    START = "start"
    STOP = "stop"
    ARCHIVE = "archive"
    FAIL = "fail"
    RESTORE = "restore"
