from fastapi import APIRouter, Depends, HTTPException, status, Header
from app.api.baas_auth_models import (
    EndUserRegisterRequest, EndUserLoginRequest, EndUserTokenResponse, 
    EndUserRefreshRequest, EndUserAccessTokenResponse, EndUserResponse,
    EndUserPasswordResetRequest, EndUserPasswordResetConfirm, EndUserVerifyEmailRequest
)
from app.api.baas_auth_service import (
    BaaSAuthService, BaaSUserAlreadyExistsException, InvalidBaaSCredentialsException, 
    InvalidBaaSRefreshTokenException
)

router = APIRouter(prefix="/{project_id}/auth", tags=["BaaS End-User Auth"])

def get_baas_auth_service():
    raise NotImplementedError("Dependency should be overridden in app startup.")

def verify_end_user_token(
    project_id: str,
    authorization: str = Header(..., description="Bearer token")
) -> str:
    # This is a dependency for endpoints that require an authenticated end-user.
    from app.auth import decode_token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token scheme")
    
    token = authorization.split(" ")[1]
    try:
        payload = decode_token(token, expected_aud="end_user")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
        
    if payload.get("project_id") != project_id:
        raise HTTPException(status_code=403, detail="Token not valid for this project")
        
    return payload.get("sub")

@router.post("/register", response_model=EndUserResponse, status_code=status.HTTP_201_CREATED)
def register(
    project_id: str,
    req: EndUserRegisterRequest,
    auth_service: BaaSAuthService = Depends(get_baas_auth_service)
):
    try:
        return auth_service.register(project_id, req)
    except BaaSUserAlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=EndUserTokenResponse)
def login(
    project_id: str,
    req: EndUserLoginRequest,
    auth_service: BaaSAuthService = Depends(get_baas_auth_service)
):
    try:
        return auth_service.login(project_id, req)
    except InvalidBaaSCredentialsException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/refresh", response_model=EndUserAccessTokenResponse)
def refresh(
    project_id: str,
    req: EndUserRefreshRequest,
    auth_service: BaaSAuthService = Depends(get_baas_auth_service)
):
    try:
        return auth_service.refresh(project_id, req)
    except InvalidBaaSRefreshTokenException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/verify-email", status_code=status.HTTP_200_OK)
def verify_email(
    project_id: str,
    req: EndUserVerifyEmailRequest,
    auth_service: BaaSAuthService = Depends(get_baas_auth_service)
):
    try:
        auth_service.verify_email(project_id, req)
        return {"status": "success"}
    except InvalidBaaSCredentialsException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/reset-password-request", status_code=status.HTTP_200_OK)
def request_password_reset(
    project_id: str,
    req: EndUserPasswordResetRequest,
    auth_service: BaaSAuthService = Depends(get_baas_auth_service)
):
    auth_service.request_password_reset(project_id, req)
    return {"status": "success"}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(
    project_id: str,
    req: EndUserPasswordResetConfirm,
    auth_service: BaaSAuthService = Depends(get_baas_auth_service)
):
    try:
        auth_service.reset_password(project_id, req)
        return {"status": "success"}
    except InvalidBaaSCredentialsException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/me", response_model=dict)
def get_me(
    project_id: str,
    user_id: str = Depends(verify_end_user_token),
    auth_service: BaaSAuthService = Depends(get_baas_auth_service)
):
    user = auth_service._auth_repo.get_user_by_id(project_id, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": user["id"],
        "email": user["email"],
        "is_verified": user["is_verified"],
        "created_at": user["created_at"]
    }
