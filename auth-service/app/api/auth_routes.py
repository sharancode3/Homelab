from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from app.api.rate_limiter import rate_limit_ip, check_auth_brute_force, clear_auth_brute_force, get_client_ip
from app.api.auth_models import UserRegisterRequest, UserLoginRequest, AuthTokenResponse, RefreshRequest, AccessTokenResponse, UserResponse
from app.api.auth_service import AuthServiceLayer, InvalidCredentialsException, UserAlreadyExistsException, InvalidRefreshTokenException
from app.identity.models import DeveloperUser
from app.api.dependencies import get_current_user, get_revocation_repo, oauth2_scheme

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
async def login(
    request: Request,
    req: UserLoginRequest, 
    background_tasks: BackgroundTasks,
    service: AuthServiceLayer = Depends(get_auth_service),
    _rate_limit: None = Depends(rate_limit_ip)
) -> AuthTokenResponse:
    await check_auth_brute_force(request, req.email)
    try:
        res = await run_in_threadpool(service.login, req)
        background_tasks.add_task(clear_auth_brute_force, get_client_ip(request), req.email)
        return res
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

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: str = Depends(oauth2_scheme),
    revocation_repo = Depends(get_revocation_repo)
):
    from app.auth import decode_token
    from datetime import datetime, timezone
    try:
        payload = decode_token(token, expected_aud="developer")
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
            revocation_repo.revoke_token(jti, expires_at)
    except Exception:
        # Ignore invalid tokens during logout
        pass
