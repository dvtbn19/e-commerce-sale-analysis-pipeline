from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

SALES_ROUTE = "/api/sales"


def _mock_engine_returning(total, rows):
    mock_engine = MagicMock()
    connection = mock_engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar.return_value = total
    connection.execute.return_value.mappings.return_value.all.return_value = rows
    return mock_engine


def test_sales_cache_hit_skips_database():
    cached_payload = {
        "page": 1,
        "page_size": 50,
        "total": 2,
        "total_pages": 1,
        "data": [{"order_id": "A1"}, {"order_id": "A2"}],
    }

    with patch(
        "app.routes.sales.get_cached_json",
        return_value=cached_payload,
    ), patch("app.routes.sales.engine") as mock_engine:
        response = client.get(SALES_ROUTE)

    assert response.status_code == 200
    assert response.json() == cached_payload
    assert response.headers["X-Cache"] == "HIT"
    mock_engine.connect.assert_not_called()


def test_sales_cache_miss_reads_db_and_sets_header():
    rows = [{"order_id": "A1"}, {"order_id": "A2"}]

    with patch(
        "app.routes.sales.get_cached_json", return_value=None
    ), patch(
        "app.routes.sales.set_cached_json", return_value=True
    ), patch(
        "app.routes.sales.engine", _mock_engine_returning(total=2, rows=rows)
    ):
        response = client.get(
            SALES_ROUTE, params={"page": 1, "page_size": 50}
        )

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"

    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["total"] == 2
    assert body["total_pages"] == 1
    assert body["data"] == rows


def test_sales_cache_bypass_when_write_fails():
    rows = [{"order_id": "A1"}]

    with patch(
        "app.routes.sales.get_cached_json", return_value=None
    ), patch(
        "app.routes.sales.set_cached_json", return_value=False
    ), patch(
        "app.routes.sales.engine", _mock_engine_returning(total=1, rows=rows)
    ):
        response = client.get(
            SALES_ROUTE, params={"page": 1, "page_size": 50}
        )

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "BYPASS"
    assert response.json()["data"] == rows


def test_ready_returns_200_when_database_ok():
    with patch("app.main.engine"):
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": True}


def test_ready_returns_503_when_database_down():
    with patch("app.main.engine") as mock_engine:
        mock_engine.connect.side_effect = RuntimeError("db down")

        response = client.get("/ready")

    assert response.status_code == 503
