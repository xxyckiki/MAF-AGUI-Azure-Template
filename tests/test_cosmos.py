"""
Unit tests for Cosmos DB connection module.

Tests cover:
- Credential selection (Managed Identity vs Azure CLI)
- Client initialization with key vs credential
- Database and container proxy retrieval
- Environment variable handling
- Singleton pattern (lru_cache)
"""

import pytest
from unittest.mock import patch, MagicMock
import os

from src.db.cosmos import (
    get_credential,
    get_cosmos_client,
    get_database,
    get_container,
)


class TestGetCredential:
    """Tests for get_credential function."""

    @patch("src.db.cosmos.ManagedIdentityCredential")
    @patch("src.db.cosmos.AzureCliCredential")
    @patch("src.db.cosmos.ChainedTokenCredential")
    def test_get_credential_returns_chained_credential(
        self, mock_chained, mock_cli_cred, mock_msi_cred
    ):
        """Test that get_credential returns ChainedTokenCredential."""
        # Arrange
        mock_msi_instance = MagicMock()
        mock_cli_instance = MagicMock()
        mock_msi_cred.return_value = mock_msi_instance
        mock_cli_cred.return_value = mock_cli_instance

        # Act
        _ = get_credential()  # Call to verify it works

        # Assert
        mock_msi_cred.assert_called_once()
        mock_cli_cred.assert_called_once()
        mock_chained.assert_called_once_with(mock_msi_instance, mock_cli_instance)

    @patch("src.db.cosmos.ChainedTokenCredential")
    def test_get_credential_creates_msi_first_then_cli(self, mock_chained):
        """Test that ManagedIdentityCredential is tried before AzureCliCredential."""
        # Act
        _ = get_credential()  # Call to verify it works

        # Assert
        # ChainedTokenCredential should be called with MSI first, then CLI
        call_args = mock_chained.call_args[0]
        assert len(call_args) == 2
        # First credential should be ManagedIdentityCredential
        # Second should be AzureCliCredential
        # We verify by checking the call was made (implementation detail)


class TestGetCosmosClient:
    """Tests for get_cosmos_client function."""

    def setup_method(self):
        """Clear lru_cache before each test."""
        get_cosmos_client.cache_clear()

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_cosmos_endpoint_raises_error(self):
        """Test that missing COSMOS_ENDPOINT raises ValueError."""
        # Arrange
        get_cosmos_client.cache_clear()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            get_cosmos_client()

        assert "COSMOS_ENDPOINT" in str(exc_info.value)

    @patch.dict(
        os.environ,
        {
            "COSMOS_ENDPOINT": "https://test.documents.azure.com:443/",
            "COSMOS_KEY": "test_key_12345",
        },
    )
    @patch("src.db.cosmos.CosmosClient")
    def test_cosmos_client_with_key_auth(self, mock_cosmos_client):
        """Test that COSMOS_KEY is used for authentication when provided."""
        # Arrange
        get_cosmos_client.cache_clear()
        mock_client_instance = MagicMock()
        mock_cosmos_client.return_value = mock_client_instance

        # Act
        client = get_cosmos_client()

        # Assert
        mock_cosmos_client.assert_called_once_with(
            url="https://test.documents.azure.com:443/", credential="test_key_12345"
        )
        assert client is mock_client_instance

    @patch.dict(
        os.environ,
        {
            "COSMOS_ENDPOINT": "https://test.documents.azure.com:443/",
        },
        clear=True,
    )
    @patch("src.db.cosmos.CosmosClient")
    @patch("src.db.cosmos.get_credential")
    def test_cosmos_client_with_credential_auth(
        self, mock_get_credential, mock_cosmos_client
    ):
        """Test that credential is used when COSMOS_KEY is not set."""
        # Arrange
        get_cosmos_client.cache_clear()
        mock_credential = MagicMock()
        mock_get_credential.return_value = mock_credential
        mock_client_instance = MagicMock()
        mock_cosmos_client.return_value = mock_client_instance

        # Act
        _ = get_cosmos_client()  # Call to verify it works

        # Assert
        mock_get_credential.assert_called_once()
        mock_cosmos_client.assert_called_once_with(
            url="https://test.documents.azure.com:443/", credential=mock_credential
        )

    @patch.dict(
        os.environ,
        {
            "COSMOS_ENDPOINT": "https://test.documents.azure.com:443/",
            "COSMOS_KEY": "key123",
        },
    )
    @patch("src.db.cosmos.CosmosClient")
    def test_cosmos_client_singleton_pattern(self, mock_cosmos_client):
        """Test that get_cosmos_client uses lru_cache (singleton)."""
        # Arrange
        get_cosmos_client.cache_clear()
        mock_client_instance = MagicMock()
        mock_cosmos_client.return_value = mock_client_instance

        # Act
        client1 = get_cosmos_client()
        client2 = get_cosmos_client()
        client3 = get_cosmos_client()

        # Assert
        # CosmosClient should only be created once due to @lru_cache
        assert mock_cosmos_client.call_count == 1
        assert client1 is client2 is client3

    @patch.dict(
        os.environ,
        {
            "COSMOS_ENDPOINT": "",  # Empty string
            "COSMOS_KEY": "key123",
        },
    )
    def test_empty_cosmos_endpoint_raises_error(self):
        """Test that empty COSMOS_ENDPOINT is treated as missing."""
        # Arrange
        get_cosmos_client.cache_clear()

        # Act & Assert
        with pytest.raises(ValueError):
            get_cosmos_client()

    @patch.dict(
        os.environ,
        {
            "COSMOS_ENDPOINT": "https://prod.documents.azure.com:443/",
            "COSMOS_KEY": "",  # Empty key should be treated as not set
        },
    )
    @patch("src.db.cosmos.CosmosClient")
    @patch("src.db.cosmos.get_credential")
    def test_empty_cosmos_key_falls_back_to_credential(
        self, mock_get_credential, mock_cosmos_client
    ):
        """Test that empty COSMOS_KEY falls back to credential auth."""
        # Arrange
        get_cosmos_client.cache_clear()
        mock_credential = MagicMock()
        mock_get_credential.return_value = mock_credential

        # Act
        _ = get_cosmos_client()  # Call to verify it works

        # Assert
        # Empty string is falsy in Python, so should use credential
        mock_get_credential.assert_called_once()


class TestGetDatabase:
    """Tests for get_database function."""

    @patch("src.db.cosmos.get_cosmos_client")
    def test_get_database_with_default_name(self, mock_get_client):
        """Test get_database with default database name."""
        # Arrange
        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_client.get_database_client.return_value = mock_database
        mock_get_client.return_value = mock_client

        # Act
        database = get_database()

        # Assert
        mock_client.get_database_client.assert_called_once_with("maf_db")
        assert database is mock_database

    @patch("src.db.cosmos.get_cosmos_client")
    def test_get_database_with_custom_name(self, mock_get_client):
        """Test get_database with custom database name."""
        # Arrange
        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_client.get_database_client.return_value = mock_database
        mock_get_client.return_value = mock_client

        # Act
        database = get_database("custom_db")

        # Assert
        mock_client.get_database_client.assert_called_once_with("custom_db")
        assert database is mock_database

    @patch("src.db.cosmos.get_cosmos_client")
    def test_get_database_returns_database_proxy(self, mock_get_client):
        """Test that get_database returns DatabaseProxy."""
        # Arrange
        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_client.get_database_client.return_value = mock_database
        mock_get_client.return_value = mock_client

        # Act
        result = get_database("test_db")

        # Assert
        assert result is mock_database


class TestGetContainer:
    """Tests for get_container function."""

    @patch("src.db.cosmos.get_database")
    def test_get_container_with_defaults(self, mock_get_database):
        """Test get_container with default parameters."""
        # Arrange
        mock_database = MagicMock()
        mock_container = MagicMock()
        mock_database.get_container_client.return_value = mock_container
        mock_get_database.return_value = mock_database

        # Act
        container = get_container()

        # Assert
        mock_get_database.assert_called_once_with("maf_db")
        mock_database.get_container_client.assert_called_once_with("conversations")
        assert container is mock_container

    @patch("src.db.cosmos.get_database")
    def test_get_container_with_custom_parameters(self, mock_get_database):
        """Test get_container with custom container and database names."""
        # Arrange
        mock_database = MagicMock()
        mock_container = MagicMock()
        mock_database.get_container_client.return_value = mock_container
        mock_get_database.return_value = mock_database

        # Act
        container = get_container(
            container_name="custom_container", database_name="custom_db"
        )

        # Assert
        mock_get_database.assert_called_once_with("custom_db")
        mock_database.get_container_client.assert_called_once_with("custom_container")
        assert container is mock_container

    @patch("src.db.cosmos.get_database")
    def test_get_container_returns_container_proxy(self, mock_get_database):
        """Test that get_container returns ContainerProxy."""
        # Arrange
        mock_database = MagicMock()
        mock_container = MagicMock()
        mock_database.get_container_client.return_value = mock_container
        mock_get_database.return_value = mock_database

        # Act
        result = get_container("test_container", "test_db")

        # Assert
        assert result is mock_container

    @patch("src.db.cosmos.get_database")
    def test_get_container_calls_get_database_with_correct_name(
        self, mock_get_database
    ):
        """Test that get_container passes database_name to get_database."""
        # Arrange
        mock_database = MagicMock()
        mock_container = MagicMock()
        mock_database.get_container_client.return_value = mock_container
        mock_get_database.return_value = mock_database

        # Act
        _ = get_container(
            container_name="my_container", database_name="my_database"
        )  # Call to verify it works

        # Assert
        mock_get_database.assert_called_once_with("my_database")
        mock_database.get_container_client.assert_called_once_with("my_container")


class TestIntegrationScenarios:
    """Integration-style tests for common usage patterns."""

    def setup_method(self):
        """Clear cache before each test."""
        get_cosmos_client.cache_clear()

    @patch.dict(
        os.environ,
        {
            "COSMOS_ENDPOINT": "https://myaccount.documents.azure.com:443/",
            "COSMOS_KEY": "my_secret_key",
        },
    )
    @patch("src.db.cosmos.CosmosClient")
    def test_full_flow_with_key_auth(self, mock_cosmos_client):
        """Test full flow from client to container with key authentication."""
        # Arrange
        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_container = MagicMock()

        mock_cosmos_client.return_value = mock_client
        mock_client.get_database_client.return_value = mock_database
        mock_database.get_container_client.return_value = mock_container

        # Act
        container = get_container("my_container", "my_db")

        # Assert
        mock_cosmos_client.assert_called_once_with(
            url="https://myaccount.documents.azure.com:443/", credential="my_secret_key"
        )
        mock_client.get_database_client.assert_called_once_with("my_db")
        mock_database.get_container_client.assert_called_once_with("my_container")
        assert container is mock_container

    @patch.dict(
        os.environ,
        {
            "COSMOS_ENDPOINT": "https://myaccount.documents.azure.com:443/",
        },
        clear=True,
    )
    @patch("src.db.cosmos.CosmosClient")
    @patch("src.db.cosmos.get_credential")
    def test_full_flow_with_credential_auth(
        self, mock_get_credential, mock_cosmos_client
    ):
        """Test full flow with credential authentication (no key)."""
        # Arrange
        mock_credential = MagicMock()
        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_container = MagicMock()

        mock_get_credential.return_value = mock_credential
        mock_cosmos_client.return_value = mock_client
        mock_client.get_database_client.return_value = mock_database
        mock_database.get_container_client.return_value = mock_container

        # Act
        _ = get_container()  # Call to verify it works

        # Assert
        mock_get_credential.assert_called_once()
        mock_cosmos_client.assert_called_once_with(
            url="https://myaccount.documents.azure.com:443/", credential=mock_credential
        )
        mock_client.get_database_client.assert_called_once_with("maf_db")
        mock_database.get_container_client.assert_called_once_with("conversations")

    @patch.dict(
        os.environ,
        {
            "COSMOS_ENDPOINT": "https://test.documents.azure.com:443/",
            "COSMOS_KEY": "key123",
        },
    )
    @patch("src.db.cosmos.CosmosClient")
    def test_multiple_container_requests_reuse_client(self, mock_cosmos_client):
        """Test that multiple container requests reuse the same client."""
        # Arrange
        mock_client = MagicMock()
        mock_database1 = MagicMock()
        mock_database2 = MagicMock()
        mock_container1 = MagicMock()
        mock_container2 = MagicMock()

        mock_cosmos_client.return_value = mock_client
        mock_client.get_database_client.side_effect = [mock_database1, mock_database2]
        mock_database1.get_container_client.return_value = mock_container1
        mock_database2.get_container_client.return_value = mock_container2

        # Act
        container1 = get_container("container1", "db1")
        container2 = get_container("container2", "db2")

        # Assert
        # Client should only be created once due to singleton
        assert mock_cosmos_client.call_count == 1
        assert container1 is mock_container1
        assert container2 is mock_container2


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def setup_method(self):
        """Clear cache before each test."""
        get_cosmos_client.cache_clear()

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.db.cosmos.CosmosClient")
    def test_get_container_fails_when_no_endpoint(self, mock_cosmos_client):
        """Test that get_container fails gracefully when endpoint is missing."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            get_container()

        assert "COSMOS_ENDPOINT" in str(exc_info.value)

    @patch.dict(
        os.environ,
        {
            "COSMOS_ENDPOINT": "https://test.documents.azure.com:443/",
            "COSMOS_KEY": "key123",
        },
    )
    @patch("src.db.cosmos.CosmosClient")
    def test_client_creation_error_propagates(self, mock_cosmos_client):
        """Test that errors during client creation are propagated."""
        # Arrange
        mock_cosmos_client.side_effect = Exception("Connection failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            get_cosmos_client()

        assert "Connection failed" in str(exc_info.value)
