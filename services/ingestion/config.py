import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ecommerce")
POSTGRES_USER = os.getenv("POSTGRES_USER", "ecommerce")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

SOURCE_CSV_PATH = Path(
    os.getenv(
        "SOURCE_CSV_PATH",
        "data/raw/ecommerce/Amazon Sale Report.csv",
    )
)


def get_database_url() -> str:
    if not POSTGRES_PASSWORD:
        raise ValueError(
            "POSTGRES_PASSWORD environment variable is not set."
        )

    return (
        f"postgresql+psycopg2://"
        f"{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )