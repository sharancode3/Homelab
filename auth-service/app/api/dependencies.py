from fastapi import Depends, HTTPException, Security, status, Header
from app.config.settings import config
import secrets
import hashlib

try:
    from fastapi.security import OAuth2PasswordBearer
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
except ModuleNotFoundError:
    oauth2_scheme = None

from app.auth import decode_token
from app.identity.models import DeveloperUser

# To avoid circular imports, we don't import get_auth_service from auth_routes.
# Instead, we define a provider here, or we can just inject the UserRepository.
# Let's inject a placeholder for UserRepository.
def get_user_repository():
    raise NotImplementedError("Dependency should be overridden in app startup.")

def get_current_user(
    token: str = Security(oauth2_scheme),
    user_repo = Depends(get_user_repository)
) -> DeveloperUser:
    payload = decode_token(token, expected_aud="developer")

    if payload.get("token_type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_repo.get_by_email(email)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

def get_authz_repo():
    raise NotImplementedError("Dependency should be overridden in app startup.")

def get_baas_project_service():
    raise NotImplementedError("Dependency should be overridden in app startup.")

class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        project_id: str,
        user: DeveloperUser = Depends(get_current_user),
        authz_repo = Depends(get_authz_repo)
    ) -> str:
        role = authz_repo.get_role(project_id, user.user_id)
        if not role or role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have sufficient permissions for this project."
            )
        return role

require_viewer = RoleChecker(["owner", "admin", "developer", "viewer"])
require_developer = RoleChecker(["owner", "admin", "developer"])
require_admin = RoleChecker(["owner", "admin"])
require_owner = RoleChecker(["owner"])

# Keep this for backwards compatibility if needed, but it checks existence
def verify_project_access(
    project_id: str,
    user: DeveloperUser = Depends(get_current_user),
    authz_repo = Depends(get_authz_repo)
) -> None:
    if not authz_repo.check_access(project_id, user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project.",
        )

def verify_project_api_key(
    project_id: str,
    x_project_api_key: str = Header(..., alias="X-Project-API-Key"),
    authz_repo = Depends(get_authz_repo)
) -> str:
    # Key format: pk_live_<key_id>_<secret>
    parts = x_project_api_key.split('_')
    if len(parts) != 4 or parts[0] != 'pk' or parts[1] != 'live':
        raise HTTPException(status_code=401, detail="Invalid API key format")

    key_id = parts[2]
    secret = parts[3]

    key_record = authz_repo.get_api_key(key_id)
    if not key_record or not key_record["is_active"]:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    if key_record["project_id"] != project_id:
        raise HTTPException(status_code=403, detail="API key not valid for this project")

    expected_hash = key_record["secret_hash"]
    actual_hash = hashlib.sha256(secret.encode('utf-8')).hexdigest()

    if not secrets.compare_digest(expected_hash, actual_hash):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return project_id

def verify_internal_token(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token")
) -> None:
    if not x_internal_token or not secrets.compare_digest(x_internal_token, config.internal_api_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal token",
        )
