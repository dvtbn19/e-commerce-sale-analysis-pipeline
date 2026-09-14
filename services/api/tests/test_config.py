import pytest

from app.core.config import LOCAL_CORS_ORIGINS, parse_cors_origins


def test_cors_origins_fall_back_to_local_defaults():
    assert parse_cors_origins(None, "local") == LOCAL_CORS_ORIGINS
    assert parse_cors_origins("", "local") == LOCAL_CORS_ORIGINS


def test_cors_origins_are_split_and_trimmed():
    raw = " https://app.example.com , https://api.example.com "

    assert parse_cors_origins(raw, "production") == [
        "https://app.example.com",
        "https://api.example.com",
    ]


def test_cors_origins_ignore_empty_entries():
    assert parse_cors_origins("https://app.example.com,,", "production") == [
        "https://app.example.com",
    ]


def test_production_refuses_to_start_without_cors_origins():
    with pytest.raises(RuntimeError, match="CORS_ALLOWED_ORIGINS"):
        parse_cors_origins(None, "production")
