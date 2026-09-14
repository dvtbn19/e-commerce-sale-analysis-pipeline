from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

from app.core.config import CORS_ALLOWED_ORIGINS
from app.db.database import engine
from app.routes.sales import router as sales_router
from app.auth.routes import router as auth_router
from app.cache.redis_client import redis_client
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="E-Commerce Sale Analysis API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sales_router)
app.include_router(auth_router)

@app.get("/live")
def liveness():
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is not ready",
        ) from exc

    return {
        "status": "ready",
        "database": True,
    }

@app.get("/")
def root():
    return {
        "message": "E-Commerce Sale Analysis API"
    }


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            database = connection.execute(
                text("SELECT current_database();")
            ).scalar()

        return {
            "status": "ok",
            "database": database,
        }

    except Exception as exc:
        return {
            "status": "error",
            "database": None,
            "detail": str(exc),
        }


@app.get("/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            count = connection.execute(
                text(
                    "SELECT COUNT(*) "
                    "FROM raw.amazon_sales;"
                )
            ).scalar()

        return {
            "status": "ok",
            "table": "raw.amazon_sales",
            "row_count": count,
        }

    except Exception as exc:
        return {
            "status": "error",
            "detail": str(exc),
        }

@app.get("/health/redis")
def redis_health():
    try:
        pong = redis_client.ping()

        return {
            "status": "ok",
            "redis": pong,
        }

    except Exception as exc:
        return {
            "status": "error",
            "redis": False,
            "detail": str(exc),
        }

# Keep monitoring traffic out of application request metrics.
Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=[r"^/metrics$", r"^/live$", r"^/ready$"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
