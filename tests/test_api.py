"""
Integration tests for API endpoints.
"""


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_200(self, client):
        """
        Test that root endpoint returns 200 OK.

        The 'client' parameter is automatically injected by pytest
        from the fixture defined in conftest.py.
        """
        response = client.get("/")

        assert response.status_code == 200

    def test_root_returns_expected_json(self, client):
        """Test root endpoint response content."""
        response = client.get("/")
        data = response.json()

        assert data["message"] == "Flight Agent API"
        assert data["version"] == "1.0.0"
        assert "docs" in data


class TestCopilotEndpoint:
    """Tests for the CopilotKit AG-UI endpoint."""

    def test_copilotkit_endpoint_exists(self, client):
        """
        Test that /copilotkit endpoint exists.

        Note: This endpoint uses AG-UI protocol, so we just verify it exists.
        A proper POST request would require AG-UI formatted data.
        """
        # GET should return 405 Method Not Allowed (endpoint exists but wrong method)
        response = client.get("/copilotkit")

        # Either 405 (method not allowed) or 422 (validation error) means endpoint exists
        assert response.status_code in [405, 422, 200]
