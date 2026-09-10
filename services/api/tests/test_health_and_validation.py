from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_live_returns_ok():
    response = client.get("/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_returns_message():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "E-Commerce Sale Analysis API"
    }


def test_sales_rejects_page_below_1():
    response = client.get("/api/sales", params={"page": 0})

    assert response.status_code == 422


def test_sales_rejects_page_size_above_100():
    response = client.get("/api/sales", params={"page_size": 101})

    assert response.status_code == 422


def test_sales_rejects_page_size_below_1():
    response = client.get("/api/sales", params={"page_size": 0})

    assert response.status_code == 422


def test_sales_rejects_non_integer_page():
    response = client.get("/api/sales", params={"page": "abc"})

    assert response.status_code == 422
