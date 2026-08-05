from enum import Enum


class Permission(str, Enum):
    DEPLOY = "deploy"
    BACKUP = "backup"
    RESTORE = "restore"
    ARCHIVE = "archive"
    HEALTH_VIEW = "health_view"


class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: {
        Permission.DEPLOY,
        Permission.BACKUP,
        Permission.RESTORE,
        Permission.ARCHIVE,
        Permission.HEALTH_VIEW,
    },
    Role.OPERATOR: {
        Permission.DEPLOY,
        Permission.BACKUP,
        Permission.RESTORE,
        Permission.HEALTH_VIEW,
    },
    Role.VIEWER: {
        Permission.HEALTH_VIEW,
    },
}
