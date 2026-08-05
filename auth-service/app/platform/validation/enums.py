from enum import Enum


class ValidationStatus(str, Enum):
    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"


class ValidationCategory(str, Enum):
    REGISTRY = "registry"
    LIFECYCLE = "lifecycle"
    CONFIGURATION = "configuration"
    SECRETS = "secrets"
    DEPENDENCIES = "dependencies"
    INFRASTRUCTURE = "infrastructure"
    OPERATION = "operation"
