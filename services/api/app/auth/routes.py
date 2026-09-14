import os

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from app.auth.security import (
    AUTH_COOKIE_NAME,
    AUTH_TOKEN_TTL_HOURS,
    create_access_token,
    get_current_user,
    verify_password,
)
from app.db.database import engine


router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)

COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(credentials: LoginRequest, response: Response):
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT username, password_hash
                FROM auth.users
                WHERE username = :username
                """
            ),
            {"username": credentials.username},
        ).mappings().one_or_none()

    if row is None or not verify_password(
        credentials.password, row["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(row["username"])

    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=AUTH_TOKEN_TTL_HOURS * 3600,
    )

    return {"username": row["username"]}


@router.post("/logout")
def logout(response: Response):
    # The clearing cookie has to carry the same flags as the one that was set,
    # otherwise the browser treats it as a different cookie and keeps the
    # session alive.
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )

    return {"status": "ok"}


@router.get("/me")
def me(current_user: str = Depends(get_current_user)):
    return {"username": current_user}
