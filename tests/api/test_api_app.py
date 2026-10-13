"""Tests for the backend application."""

from court_booker import __version__
from court_booker.api.context import Context


def test_health_reports_the_version(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_the_openapi_schema_is_served_under_api(client):
    schema = client.get("/api/openapi.json").json()

    assert schema["info"]["title"] == "Court Booker"
    assert "/api/health" in schema["paths"]


def test_routes_get_the_context(app, client, context):
    @app.get("/api/test-context")
    def read(context: Context) -> dict:
        return {"config": str(context.config_path), "days": context.config().days_ahead}

    assert client.get("/api/test-context").json() == {
        "config": str(context.config_path),
        "days": 2,
    }
