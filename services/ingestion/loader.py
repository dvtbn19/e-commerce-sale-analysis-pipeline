from pathlib import Path
import re

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from services.ingestion.config import (
    SOURCE_CSV_PATH,
    get_database_url,
)


def normalize_column_name(column: str) -> str:
    column = column.strip().lower()
    column = re.sub(r"[^a-z0-9]+", "_", column)
    column = column.strip("_")
    return column


def ingest_amazon_sales(
    csv_path: str | Path | None = None,
) -> dict:
    """
    Load Amazon sales CSV into raw.amazon_sales.

    Returns metadata that can be logged by CLI or Airflow.
    """

    source_path = (
        Path(csv_path)
        if csv_path is not None
        else SOURCE_CSV_PATH
    )

    if not source_path.exists():
        raise FileNotFoundError(
            f"CSV not found: {source_path}"
        )

    print(f"Reading CSV: {source_path}")

    df = pd.read_csv(
        source_path,
        low_memory=False,
    )

    source_row_count = len(df)

    print(f"Rows found: {source_row_count}")
    print(f"Columns found: {len(df.columns)}")

    df.columns = [
        normalize_column_name(column)
        for column in df.columns
    ]

    print("Normalized columns:")
    for column in df.columns:
        print(f"- {column}")

    engine = create_engine(
        get_database_url(),
        pool_pre_ping=True,
    )

    with engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT current_database();")
        ).scalar()

    print(
        f"Connected to PostgreSQL database: "
        f"{database_name}"
    )

    print(
        "Loading data into raw.amazon_sales..."
    )

    with engine.begin() as connection:
        connection.execute(
            text("CREATE SCHEMA IF NOT EXISTS raw;")
        )

        inspector = inspect(connection)

        table_exists = inspector.has_table(
            "amazon_sales",
            schema="raw",
        )

        if table_exists:
            print("raw.amazon_sales exists. Truncating existing data...")

            connection.execute(
                text("TRUNCATE TABLE raw.amazon_sales;")
            )
        else:
            print(
                "raw.amazon_sales does not exist. "
                "Creating table on first load..."
            )

        df.to_sql(
            name="amazon_sales",
            con=connection,
            schema="raw",
            if_exists="append",
            index=False,
            chunksize=5000,
            method="multi",
        )

    with engine.connect() as connection:
        database_row_count = connection.execute(
            text(
                "SELECT COUNT(*) "
                "FROM raw.amazon_sales;"
            )
        ).scalar()

    if source_row_count != database_row_count:
        raise ValueError(
            "Row count mismatch: "
            f"source={source_row_count}, "
            f"database={database_row_count}"
        )

    print(
        "SUCCESS: CSV and PostgreSQL "
        "row counts match."
    )

    return {
        "status": "success",
        "source": str(source_path),
        "table": "raw.amazon_sales",
        "source_rows": source_row_count,
        "database_rows": database_row_count,
    }