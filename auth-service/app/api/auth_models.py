from pydantic import BaseModel, EmailStr


class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    """Returned by POST /auth/refresh — issues a new access token only."""
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Carries the long-lived refresh token."""
    refresh_token: str


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    is_active: bool
