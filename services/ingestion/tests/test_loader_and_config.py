import pytest

from services.ingestion import config
from services.ingestion.loader import (
    ingest_amazon_sales,
    normalize_column_name,
)


@pytest.mark.parametrize(
    "raw_column,expected",
    [
        ("Order ID", "order_id"),
        ("  Amount  ", "amount"),
        ("ship-postal-code", "ship_postal_code"),
        ("Qty (units)", "qty_units"),
        ("B2B?", "b2b"),
        ("__weird__NAME__", "weird_name"),
        ("a - b", "a_b"),
    ],
)
def test_normalize_column_name(raw_column, expected):
    assert normalize_column_name(raw_column) == expected


def test_get_database_url_builds_expected_dsn(monkeypatch):
    monkeypatch.setattr(config, "POSTGRES_USER", "ecommerce")
    monkeypatch.setattr(config, "POSTGRES_PASSWORD", "secret")
    monkeypatch.setattr(config, "POSTGRES_HOST", "localhost")
    monkeypatch.setattr(config, "POSTGRES_PORT", "5433")
    monkeypatch.setattr(config, "POSTGRES_DB", "ecommerce")

    assert config.get_database_url() == (
        "postgresql+psycopg2://ecommerce:secret@localhost:5433/ecommerce"
    )


def test_get_database_url_raises_without_password(monkeypatch):
    monkeypatch.setattr(config, "POSTGRES_PASSWORD", None)

    with pytest.raises(ValueError):
        config.get_database_url()


def test_ingest_amazon_sales_raises_when_csv_missing():
    with pytest.raises(FileNotFoundError):
        ingest_amazon_sales(csv_path="does/not/exist_1234.csv")
