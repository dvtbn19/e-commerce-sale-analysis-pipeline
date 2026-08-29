from fastapi import FastAPI
from sqlalchemy import text

from app.db.database import engine
from app.routes.sales import router as sales_router
from app.cache.redis_client import redis_client
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="E-Commerce Sale Analysis API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sales_router)


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