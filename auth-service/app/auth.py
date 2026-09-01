from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext

from app.config import config

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def decode_token(token: str, expected_aud: str | None = None):
    try:
        kwargs = {}
        if expected_aud:
            kwargs["audience"] = expected_aud
        return jwt.decode(
            token,
            config.secret_key,
            algorithms=["HS256"],
            **kwargs
        )
    except (ExpiredSignatureError, InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(data: dict, aud: str = "developer", project_id: str | None = None):
    return _create_token(
        data=data,
        expires_delta=timedelta(minutes=30),
        token_type="access",
        aud=aud,
        project_id=project_id
    )


def create_refresh_token(data: dict, aud: str = "developer", project_id: str | None = None):
    return _create_token(
        data=data,
        expires_delta=timedelta(days=7),
        token_type="refresh",
        aud=aud,
        project_id=project_id
    )


def _create_token(data: dict, expires_delta: timedelta, token_type: str | None = None, aud: str = "developer", project_id: str | None = None):
    to_encode = data.copy()
    import uuid
    to_encode["jti"] = str(uuid.uuid4())

    if token_type:
        to_encode["token_type"] = token_type

    to_encode["aud"] = aud
    if project_id:
        to_encode["project_id"] = project_id

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        config.secret_key,
        algorithm="HS256",
    )