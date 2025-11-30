"""
Pytest configuration and shared fixtures.

Fixtures are reusable test components that can be injected into test functions.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI app.

    This fixture is used to make HTTP requests to the API in tests.
    The 'yield' allows cleanup after the test if needed.
    """
    from main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_flight_data():
    """
    Sample flight data for testing.

    Fixtures can return any data that tests need.
    """
    return {
        "departure": "Beijing",
        "destination": "Tokyo",
        "price": 350.0,
        "currency": "USD",
        "airline": "Air China",
        "flight_class": "Economy",
    }
