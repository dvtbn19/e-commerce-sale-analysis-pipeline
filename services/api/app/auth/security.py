import os
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt


from app.core.config import APP_ENV


def _read_jwt_secret() -> str:
    secret = os.getenv("AUTH_JWT_SECRET")

    if secret:
        return secret

    if APP_ENV == "production":
        raise RuntimeError(
            "AUTH_JWT_SECRET must be set when APP_ENV=production"
        )

    # The fallback is published in this repository, so it is only ever safe
    # for local development and the test suite.
    return "dev-insecure-change-me"


AUTH_JWT_SECRET = _read_jwt_secret()
AUTH_JWT_ALGORITHM = "HS256"
AUTH_TOKEN_TTL_HOURS = 8
AUTH_COOKIE_NAME = "access_token"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=AUTH_TOKEN_TTL_HOURS)
    payload = {"sub": username, "exp": expire}

    return jwt.encode(payload, AUTH_JWT_SECRET, algorithm=AUTH_JWT_ALGORITHM)


def get_current_user(
    access_token: str | None = Cookie(default=None),
) -> str:
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(
            access_token,
            AUTH_JWT_SECRET,
            algorithms=[AUTH_JWT_ALGORITHM],
        )
        username = payload.get("sub")

        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        return username

    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
