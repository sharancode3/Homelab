from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
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


def decode_token(token: str):
    try:
        return jwt.decode(
            token,
            config.secret_key,
            algorithms=["HS256"],
        )
    except (ExpiredSignatureError, JWTError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(data: dict):
    return _create_token(
        data=data,
        expires_delta=timedelta(minutes=30),
        token_type="access",
    )


def create_refresh_token(data: dict):
    return _create_token(
        data=data,
        expires_delta=timedelta(days=7),
        token_type="refresh",
    )


def _create_token(data: dict, expires_delta: timedelta, token_type: str | None = None):
    to_encode = data.copy()

    if token_type:
        to_encode["token_type"] = token_type

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        config.secret_key,
        algorithm="HS256",
    )