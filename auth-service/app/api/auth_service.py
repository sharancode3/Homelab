import secrets
from datetime import datetime, timezone
from app.auth import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.identity.models import DeveloperUser
from app.storage.interfaces import UserRepository
from app.storage.exceptions import DuplicateRecordError
from app.api.auth_models import UserRegisterRequest, UserLoginRequest, AuthTokenResponse, AccessTokenResponse, RefreshRequest
from app.security.hardening.validation import InputValidator

class AuthException(Exception):
    pass

class InvalidCredentialsException(AuthException):
    pass


class InvalidRefreshTokenException(AuthException):
    pass

class UserAlreadyExistsException(AuthException):
    pass

class AuthServiceLayer:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    def register(self, req: UserRegisterRequest) -> DeveloperUser:
        InputValidator.validate_payload(req.model_dump())
        
        user_id = f"usr_{secrets.token_hex(8)}"
        new_user = DeveloperUser(
            user_id=user_id,
            username=req.username,
            email=req.email,
            hashed_password=hash_password(req.password),
            created_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        try:
            self._user_repo.create(new_user)
        except DuplicateRecordError:
            raise UserAlreadyExistsException("A user with this email or username already exists.")
            
        return new_user

    def login(self, req: UserLoginRequest) -> AuthTokenResponse:
        InputValidator.validate_payload(req.model_dump())
        
        user = self._user_repo.get_by_email(req.email)
        if not user or not user.is_active:
            raise InvalidCredentialsException("Invalid email or password.")
            
        if not verify_password(req.password, user.hashed_password):
            raise InvalidCredentialsException("Invalid email or password.")
            
        access_token = create_access_token({"sub": user.user_id, "email": user.email})
        refresh_token = create_refresh_token({"sub": user.user_id, "email": user.email})
        
        return AuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    def refresh(self, req: RefreshRequest) -> AccessTokenResponse:
        """Exchange a valid refresh token for a new access token.

        The refresh token is validated (signature + expiry + token_type).
        A new access token is issued. The refresh token itself is not
        rotated at Phase 12 (no token blacklist yet).
        """
        try:
            payload = decode_token(req.refresh_token)
        except Exception:
            raise InvalidRefreshTokenException("Invalid or expired refresh token.")

        if payload.get("token_type") != "refresh":
            raise InvalidRefreshTokenException("Token is not a refresh token.")

        user_id = payload.get("sub")
        email = payload.get("email")
        if not user_id or not email:
            raise InvalidRefreshTokenException("Refresh token is missing required claims.")

        # Verify user still exists and is active
        user = self._user_repo.get_by_user_id(user_id)
        if not user or not user.is_active:
            raise InvalidRefreshTokenException("User account is inactive or does not exist.")

        new_access_token = create_access_token({"sub": user_id, "email": email})
        return AccessTokenResponse(access_token=new_access_token)
