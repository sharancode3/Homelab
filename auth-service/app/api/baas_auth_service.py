import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from app.auth import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.storage.providers.sqlite_tenant import BaaSAuthRepository, TenantDatabaseError
from app.api.baas_auth_models import (
    EndUserRegisterRequest, EndUserLoginRequest, EndUserTokenResponse, 
    EndUserRefreshRequest, EndUserAccessTokenResponse, EndUserResponse,
    EndUserPasswordResetRequest, EndUserPasswordResetConfirm, EndUserVerifyEmailRequest
)
from app.security.hardening.validation import InputValidator
from app.services.email_service import EmailProvider

class BaaSAuthException(Exception):
    pass

class InvalidBaaSCredentialsException(BaaSAuthException):
    pass

class InvalidBaaSRefreshTokenException(BaaSAuthException):
    pass

class BaaSUserAlreadyExistsException(BaaSAuthException):
    pass

class BaaSAuthService:
    def __init__(self, auth_repo: BaaSAuthRepository, email_provider: EmailProvider):
        self._auth_repo = auth_repo
        self._email_provider = email_provider

    def register(self, project_id: str, req: EndUserRegisterRequest) -> EndUserResponse:
        InputValidator.validate_payload(req.model_dump())
        
        user_id = f"endusr_{secrets.token_hex(8)}"
        verification_token = secrets.token_hex(16)
        hashed_verification_token = hashlib.sha256(verification_token.encode()).hexdigest()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        
        user_data = {
            "id": user_id,
            "email": req.email,
            "hashed_password": hash_password(req.password),
            "is_verified": False,
            "verification_token": hashed_verification_token,
            "token_expires_at": expires_at,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            self._auth_repo.create_user(project_id, user_data)
        except TenantDatabaseError as e:
            if "already exists" in str(e):
                raise BaaSUserAlreadyExistsException("A user with this email already exists.")
            raise
            
        self._email_provider.send_verification_email(req.email, verification_token, project_id)
            
        return EndUserResponse(
            id=user_id,
            email=req.email,
            is_verified=False,
            created_at=user_data["created_at"]
        )

    def login(self, project_id: str, req: EndUserLoginRequest) -> EndUserTokenResponse:
        InputValidator.validate_payload(req.model_dump())
        
        self._auth_repo.setup_schema(project_id) # ensure schema exists
        user = self._auth_repo.get_user_by_email(project_id, req.email)
        
        if not user or not verify_password(req.password, user["hashed_password"]):
            raise InvalidBaaSCredentialsException("Invalid email or password.")
            
        access_token = create_access_token(
            {"sub": user["id"], "email": user["email"]}, 
            aud="end_user", 
            project_id=project_id
        )
        refresh_token = create_refresh_token(
            {"sub": user["id"], "email": user["email"]}, 
            aud="end_user", 
            project_id=project_id
        )
        
        return EndUserTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    def refresh(self, project_id: str, req: EndUserRefreshRequest) -> EndUserAccessTokenResponse:
        try:
            payload = decode_token(req.refresh_token, expected_aud="end_user")
        except Exception:
            raise InvalidBaaSRefreshTokenException("Invalid or expired refresh token.")

        if payload.get("token_type") != "refresh":
            raise InvalidBaaSRefreshTokenException("Token is not a refresh token.")

        if payload.get("project_id") != project_id:
            raise InvalidBaaSRefreshTokenException("Token is not valid for this project.")

        user_id = payload.get("sub")
        email = payload.get("email")
        if not user_id or not email:
            raise InvalidBaaSRefreshTokenException("Refresh token is missing required claims.")

        user = self._auth_repo.get_user_by_id(project_id, user_id)
        if not user:
            raise InvalidBaaSRefreshTokenException("User account does not exist.")

        new_access_token = create_access_token(
            {"sub": user_id, "email": email},
            aud="end_user",
            project_id=project_id
        )
        return EndUserAccessTokenResponse(access_token=new_access_token)

    def verify_email(self, project_id: str, req: EndUserVerifyEmailRequest) -> bool:
        self._auth_repo.setup_schema(project_id)
        hashed_token = hashlib.sha256(req.verification_token.encode()).hexdigest()
        with self._auth_repo.factory.connect(project_id) as conn:
            cursor = conn.execute("SELECT id, token_expires_at FROM _baas_auth_users WHERE verification_token = ? AND is_verified = 0", (hashed_token,))
            row = cursor.fetchone()
            if not row:
                raise InvalidBaaSCredentialsException("Invalid verification token")
                
            if row["token_expires_at"]:
                expires_at = datetime.fromisoformat(row["token_expires_at"])
                if datetime.now(timezone.utc) > expires_at:
                    raise InvalidBaaSCredentialsException("Verification token expired")
                
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE _baas_auth_users SET is_verified = 1, verification_token = NULL, token_expires_at = NULL WHERE id = ?", (row["id"],))
            conn.execute("COMMIT")
            return True
        
    def request_password_reset(self, project_id: str, req: EndUserPasswordResetRequest) -> bool:
        self._auth_repo.setup_schema(project_id)
        user = self._auth_repo.get_user_by_email(project_id, req.email)
        if not user:
            # Enumerate safe
            return True
            
        reset_token = secrets.token_hex(16)
        hashed_reset_token = hashlib.sha256(reset_token.encode()).hexdigest()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        
        self._auth_repo.update_user(project_id, user["id"], {
            "reset_token": hashed_reset_token,
            "token_expires_at": expires_at
        })
        
        self._email_provider.send_password_reset_email(req.email, reset_token, project_id)
        return True
        
    def reset_password(self, project_id: str, req: EndUserPasswordResetConfirm) -> bool:
        self._auth_repo.setup_schema(project_id)
        hashed_token = hashlib.sha256(req.reset_token.encode()).hexdigest()
        with self._auth_repo.factory.connect(project_id) as conn:
            cursor = conn.execute("SELECT id, token_expires_at FROM _baas_auth_users WHERE reset_token = ?", (hashed_token,))
            row = cursor.fetchone()
            if not row:
                raise InvalidBaaSCredentialsException("Invalid reset token")
                
            expires_at = datetime.fromisoformat(row["token_expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                raise InvalidBaaSCredentialsException("Reset token expired")
                
            hashed_pwd = hash_password(req.new_password)
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE _baas_auth_users SET hashed_password = ?, reset_token = NULL, token_expires_at = NULL WHERE id = ?", (hashed_pwd, row["id"]))
            conn.execute("COMMIT")
            return True
