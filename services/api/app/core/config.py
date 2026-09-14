import os

from dotenv import load_dotenv


load_dotenv()


POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ecommerce")
POSTGRES_USER = os.getenv("POSTGRES_USER", "ecommerce")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_TTL_SECONDS = int(
    os.getenv("REDIS_TTL_SECONDS", "300")
)


# "local" or "production". Anything that would be unsafe to leave at a
# development default is required outright once this is "production", so a
# missing secret fails the container at startup instead of quietly running
# with a value that is public in this repository.
APP_ENV = os.getenv("APP_ENV", "local")

LOCAL_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://ecommerce.local",
]


def parse_cors_origins(raw: str | None, app_env: str) -> list[str]:
    origins = [
        origin.strip()
        for origin in (raw or "").split(",")
        if origin.strip()
    ]

    if origins:
        return origins

    if app_env == "production":
        raise RuntimeError(
            "CORS_ALLOWED_ORIGINS must be set when APP_ENV=production"
        )

    return LOCAL_CORS_ORIGINS


CORS_ALLOWED_ORIGINS = parse_cors_origins(
    os.getenv("CORS_ALLOWED_ORIGINS"),
    APP_ENV,
)