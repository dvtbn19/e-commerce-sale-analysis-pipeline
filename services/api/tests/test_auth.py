from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.auth.security import create_access_token, hash_password
from app.main import app


client = TestClient(app)


def _mock_engine_with_user(username, password_hash):
    mock_engine = MagicMock()
    connection = mock_engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.mappings.return_value.one_or_none.return_value = {
        "username": username,
        "password_hash": password_hash,
    }
    return mock_engine


def test_login_succeeds_with_valid_credentials():
    password_hash = hash_password("correct-horse-battery-staple")

    with patch(
        "app.auth.routes.engine",
        _mock_engine_with_user("admin", password_hash),
    ):
        response = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "correct-horse-battery-staple",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"username": "admin"}
    assert "access_token" in response.cookies


def test_login_rejects_wrong_password():
    password_hash = hash_password("correct-horse-battery-staple")

    with patch(
        "app.auth.routes.engine",
        _mock_engine_with_user("admin", password_hash),
    ):
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )

    assert response.status_code == 401


def test_login_rejects_unknown_username():
    mock_engine = MagicMock()
    connection = mock_engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.mappings.return_value.one_or_none.return_value = None

    with patch("app.auth.routes.engine", mock_engine):
        response = client.post(
            "/api/auth/login",
            json={"username": "ghost", "password": "whatever"},
        )

    assert response.status_code == 401


def test_me_requires_cookie():
    client.cookies.clear()

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_returns_username_with_valid_token():
    token = create_access_token("admin")
    client.cookies.set("access_token", token)

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {"username": "admin"}

    client.cookies.clear()


def test_logout_clears_cookie():
    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert "access_token=" in response.headers.get("set-cookie", "")
