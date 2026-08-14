from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class EndUserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class EndUserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class EndUserTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    
class EndUserRefreshRequest(BaseModel):
    refresh_token: str
    
class EndUserAccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class EndUserPasswordResetRequest(BaseModel):
    email: EmailStr
    
class EndUserPasswordResetConfirm(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8)

class EndUserVerifyEmailRequest(BaseModel):
    verification_token: str

class EndUserResponse(BaseModel):
    id: str
    email: str
    is_verified: bool
    created_at: str
