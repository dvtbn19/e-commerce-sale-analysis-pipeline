from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from app.main import app
from app.routes.sales import RATE_LIMIT_MAX_REQUESTS


client = TestClient(app)


VALID_PAYLOAD = {
    "category": "Kurta",
    "quantity": 2,
    "amount": 499.5,
    "ship_city": "Hanoi",
    "ship_state": "Hanoi",
}


def _authenticate():
    client.cookies.clear()
    client.cookies.set("access_token", create_access_token("admin"))


def _mock_engine(source_row_id=128977):
    mock_engine = MagicMock()
    connection = mock_engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one.return_value = source_row_id
    return mock_engine, connection


def _mock_redis(request_count=1):
    """Redis stub whose INCR returns a real int, as the live client does."""
    mock_redis = MagicMock()
    mock_redis.incr.return_value = request_count
    return mock_redis


def _executed_sql(connection):
    return " ".join(
        str(call.args[0]) for call in connection.execute.call_args_list
    )


def test_create_sale_requires_authentication():
    client.cookies.clear()

    response = client.post("/api/sales", json=VALID_PAYLOAD)

    assert response.status_code == 401


def test_create_sale_returns_created_row():
    _authenticate()
    mock_engine, _ = _mock_engine(source_row_id=128977)

    with patch("app.routes.sales.engine", mock_engine), patch(
        "app.routes.sales.redis_client", _mock_redis()
    ), patch("app.routes.sales.invalidate_sales_cache") as invalidate:
        response = client.post("/api/sales", json=VALID_PAYLOAD)

    client.cookies.clear()

    assert response.status_code == 201

    body = response.json()

    assert body["source_row_id"] == 128977
    assert body["order_id"].startswith("MANUAL-")
    assert body["category"] == "Kurta"
    assert body["quantity"] == 2
    assert body["amount"] == 499.5

    invalidate.assert_called_once()


def test_create_sale_writes_fact_table_and_rebuilds_aggregates():
    _authenticate()
    mock_engine, connection = _mock_engine()

    with patch("app.routes.sales.engine", mock_engine), patch(
        "app.routes.sales.redis_client", _mock_redis()
    ), patch("app.routes.sales.invalidate_sales_cache"):
        response = client.post("/api/sales", json=VALID_PAYLOAD)

    client.cookies.clear()

    assert response.status_code == 201

    sql = _executed_sql(connection)

    assert "INSERT INTO raw.amazon_sales" in sql
    assert "INSERT INTO analytics.fct_sales" in sql
    assert "TRUNCATE analytics.sales_summary" in sql
    assert "TRUNCATE analytics.sales_by_category" in sql


def test_create_sale_rejects_unknown_category():
    _authenticate()

    response = client.post(
        "/api/sales",
        json={**VALID_PAYLOAD, "category": "Laptop"},
    )

    client.cookies.clear()

    assert response.status_code == 422


def test_create_sale_rejects_non_positive_quantity():
    _authenticate()

    response = client.post(
        "/api/sales",
        json={**VALID_PAYLOAD, "quantity": 0},
    )

    client.cookies.clear()

    assert response.status_code == 422


def test_create_sale_rejects_non_positive_amount():
    _authenticate()

    response = client.post(
        "/api/sales",
        json={**VALID_PAYLOAD, "amount": 0},
    )

    client.cookies.clear()

    assert response.status_code == 422


def test_create_sale_rejects_overlong_ship_city():
    _authenticate()

    response = client.post(
        "/api/sales",
        json={**VALID_PAYLOAD, "ship_city": "x" * 129},
    )

    client.cookies.clear()

    assert response.status_code == 422


def test_create_sale_rejects_request_over_rate_limit():
    _authenticate()
    mock_engine, _ = _mock_engine()

    over_limit_redis = _mock_redis(request_count=RATE_LIMIT_MAX_REQUESTS + 1)

    with patch("app.routes.sales.engine", mock_engine), patch(
        "app.routes.sales.redis_client", over_limit_redis
    ), patch("app.routes.sales.invalidate_sales_cache"):
        response = client.post("/api/sales", json=VALID_PAYLOAD)

    client.cookies.clear()

    assert response.status_code == 429
    mock_engine.begin.assert_not_called()
