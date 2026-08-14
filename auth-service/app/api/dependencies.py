from fastapi import Depends, HTTPException, Security, status

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
    payload = decode_token(token)
    
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
