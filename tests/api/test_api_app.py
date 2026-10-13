"""Tests for the backend application."""

import pytest
from fastapi.testclient import TestClient

from court_booker import __version__
from court_booker.api.app import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        yield client


def test_health_reports_the_version(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_the_openapi_schema_is_served_under_api(client):
    schema = client.get("/api/openapi.json").json()

    assert schema["info"]["title"] == "Court Booker"
    assert "/api/health" in schema["paths"]
