"""Test configuration and shared fixtures for activity API tests."""
import pytest
from copy import deepcopy
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Fixture: FastAPI TestClient for making API requests."""
    return TestClient(app)


@pytest.fixture
def fresh_activities():
    """Fixture: Fresh copy of activities data for each test."""
    return deepcopy(activities)


@pytest.fixture
def mock_activities(fresh_activities, monkeypatch):
    """Fixture: Replace app activities with fresh copy to avoid test pollution."""
    monkeypatch.setattr("src.app.activities", fresh_activities)
    return fresh_activities
