from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Depends
from app.api.rate_limiter import rate_limit_ip
from app.api.auth_models import UserRegisterRequest, UserLoginRequest, AuthTokenResponse, RefreshRequest, AccessTokenResponse, UserResponse
from app.api.auth_service import AuthServiceLayer, InvalidCredentialsException, UserAlreadyExistsException, InvalidRefreshTokenException
from app.identity.models import DeveloperUser
from app.api.dependencies import get_current_user

# Dependency placeholder to be overridden in main.py
def get_auth_service() -> AuthServiceLayer:
    raise NotImplementedError("Dependency should be overridden in app startup.")

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    req: UserRegisterRequest, 
    service: AuthServiceLayer = Depends(get_auth_service),
    _rate_limit: None = Depends(rate_limit_ip)
) -> UserResponse:
    try:
        user = service.register(req)
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            is_active=user.is_active
        )
    except UserAlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=AuthTokenResponse)
def login(
    req: UserLoginRequest, 
    service: AuthServiceLayer = Depends(get_auth_service),
    _rate_limit: None = Depends(rate_limit_ip)
) -> AuthTokenResponse:
    try:
        return service.login(req)
    except InvalidCredentialsException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: DeveloperUser = Depends(get_current_user),
    _rate_limit: None = Depends(rate_limit_ip)
) -> UserResponse:
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_token(
    req: RefreshRequest,
    service: AuthServiceLayer = Depends(get_auth_service),
    _rate_limit: None = Depends(rate_limit_ip)
) -> AccessTokenResponse:
    """Exchange a valid refresh token for a new access token.

    Accepts the refresh_token issued at login. Returns a new access_token.
    The refresh token itself is not rotated (no blacklist at Phase 12).
    """
    try:
        return service.refresh(req)
    except InvalidRefreshTokenException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
