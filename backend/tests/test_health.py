"""Smoke tests for the API scaffold."""

from __future__ import annotations

from fastapi.testclient import TestClient

from healthadvocate.api.main import create_app


def test_health_returns_ok() -> None:
    # Arrange
    client = TestClient(create_app())

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
