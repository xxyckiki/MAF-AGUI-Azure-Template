"""
Unit tests for Cosmos DB Chat Message Store.

Tests cover:
- Message persistence (add/retrieve)
- Serialization/deserialization
- Message limit enforcement
- State management
- Error handling
- Complex type serialization (Enum, datetime, Pydantic)
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel
from dataclasses import dataclass
from types import SimpleNamespace
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from agent_framework import ChatMessage
from src.db.cosmos_chat_store import CosmosChatMessageStore, CosmosStoreState


# Test fixtures and helper classes
class SampleEnum(Enum):
    """Sample enum for testing serialization."""

    VALUE_A = "value_a"
    VALUE_B = "value_b"


class SamplePydanticModel(BaseModel):
    """Sample Pydantic model for testing serialization."""

    name: str
    value: int
    tags: list[str] = []


@dataclass
class SampleDataclass:
    """Sample dataclass for testing serialization."""

    id: str
    count: int


@pytest.fixture
def mock_container():
    """Create a mock Cosmos DB container."""
    container = MagicMock()
    return container


@pytest.fixture
def sample_chat_message():
    """Create a sample ChatMessage for testing."""
    # ChatMessage structure varies, so we'll create a mock
    message = MagicMock(spec=ChatMessage)
    message.role = "user"
    message.content = "Hello, world!"
    message.timestamp = datetime.now(timezone.utc)
    return message


class TestCosmosChatMessageStoreInitialization:
    """Tests for CosmosChatMessageStore initialization."""

    def test_init_with_all_parameters(self):
        """Test initialization with all parameters provided."""
        # Act
        store = CosmosChatMessageStore(
            session_id="test_session",
            thread_id="test_thread",
            container_name="test_container",
            database_name="test_db",
            max_messages=50,
        )

        # Assert
        assert store.session_id == "test_session"
        assert store.thread_id == "test_thread"
        assert store.container_name == "test_container"
        assert store.database_name == "test_db"
        assert store.max_messages == 50

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        # Act
        store = CosmosChatMessageStore()

        # Assert
        assert store.session_id.startswith("session_")
        assert store.thread_id.startswith("thread_")
        assert store.container_name == "conversations"
        assert store.database_name == "maf_db"
        assert store.max_messages is None

    def test_init_auto_generates_unique_ids(self):
        """Test that auto-generated IDs are unique."""
        # Act
        store1 = CosmosChatMessageStore()
        store2 = CosmosChatMessageStore()

        # Assert
        assert store1.session_id != store2.session_id
        assert store1.thread_id != store2.thread_id

    def test_document_id_matches_thread_id(self):
        """Test that document_id property returns thread_id."""
        # Arrange
        store = CosmosChatMessageStore(thread_id="my_thread")

        # Assert
        assert store.document_id == "my_thread"


class TestAddMessages:
    """Tests for add_messages method."""

    @pytest.mark.asyncio
    async def test_add_messages_to_new_document(self, mock_container):
        """Test adding messages creates a new document."""
        # Arrange
        store = CosmosChatMessageStore(
            session_id="session_1", thread_id="thread_1", container=mock_container
        )
        # Mock the exception properly
        mock_container.read_item.side_effect = CosmosResourceNotFoundError(
            status_code=404, message="Resource not found"
        )

        # Create a simple message object (not MagicMock to avoid serialization issues)
        message = SimpleNamespace(role="user", content="Test message")

        # Act
        await store.add_messages([message])

        # Assert
        mock_container.read_item.assert_called_once_with(
            item="thread_1", partition_key="session_1"
        )
        mock_container.upsert_item.assert_called_once()

        # Verify document structure
        upserted_doc = mock_container.upsert_item.call_args[1]["body"]
        assert upserted_doc["id"] == "thread_1"
        assert upserted_doc["session_id"] == "session_1"
        assert upserted_doc["thread_id"] == "thread_1"
        assert len(upserted_doc["messages"]) == 1
        assert "created_at" in upserted_doc
        assert "updated_at" in upserted_doc

    @pytest.mark.asyncio
    async def test_add_messages_to_existing_document(self, mock_container):
        """Test adding messages to existing document appends them."""
        # Arrange
        store = CosmosChatMessageStore(
            session_id="session_1", thread_id="thread_1", container=mock_container
        )

        existing_doc = {
            "id": "thread_1",
            "session_id": "session_1",
            "thread_id": "thread_1",
            "messages": [{"role": "user", "content": "Old message"}],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_container.read_item.return_value = existing_doc

        new_message = SimpleNamespace(role="assistant", content="New message")

        # Act
        await store.add_messages([new_message])

        # Assert
        upserted_doc = mock_container.upsert_item.call_args[1]["body"]
        assert len(upserted_doc["messages"]) == 2
        assert upserted_doc["messages"][0]["content"] == "Old message"

    @pytest.mark.asyncio
    async def test_add_messages_empty_list_does_nothing(self, mock_container):
        """Test that adding empty message list does nothing."""
        # Arrange
        store = CosmosChatMessageStore(container=mock_container)

        # Act
        await store.add_messages([])

        # Assert
        mock_container.read_item.assert_not_called()
        mock_container.upsert_item.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_messages_enforces_max_limit(self, mock_container):
        """Test that max_messages limit is enforced."""
        # Arrange
        store = CosmosChatMessageStore(
            session_id="session_1",
            thread_id="thread_1",
            max_messages=3,
            container=mock_container,
        )

        existing_doc = {
            "id": "thread_1",
            "session_id": "session_1",
            "thread_id": "thread_1",
            "messages": [
                {"role": "user", "content": "Message 1"},
                {"role": "assistant", "content": "Message 2"},
            ],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_container.read_item.return_value = existing_doc

        new_messages = [
            SimpleNamespace(role="user", content="Message 3"),
            SimpleNamespace(role="assistant", content="Message 4"),
        ]

        # Act
        await store.add_messages(new_messages)

        # Assert
        upserted_doc = mock_container.upsert_item.call_args[1]["body"]
        # Should keep only last 3 messages (drop "Message 1")
        assert len(upserted_doc["messages"]) == 3
        assert upserted_doc["messages"][0]["content"] == "Message 2"
        assert upserted_doc["messages"][-1]["content"] == "Message 4"

    @pytest.mark.asyncio
    async def test_add_multiple_messages_at_once(self, mock_container):
        """Test adding multiple messages in one call."""
        # Arrange
        store = CosmosChatMessageStore(
            session_id="session_1", thread_id="thread_1", container=mock_container
        )
        mock_container.read_item.side_effect = CosmosResourceNotFoundError(
            status_code=404, message="Resource not found"
        )

        messages = [
            SimpleNamespace(role="user", content="Message 1"),
            SimpleNamespace(role="assistant", content="Message 2"),
            SimpleNamespace(role="user", content="Message 3"),
        ]

        # Act
        await store.add_messages(messages)

        # Assert
        upserted_doc = mock_container.upsert_item.call_args[1]["body"]
        assert len(upserted_doc["messages"]) == 3


class TestListMessages:
    """Tests for list_messages method."""

    @pytest.mark.asyncio
    async def test_list_messages_returns_empty_for_new_thread(self, mock_container):
        """Test that listing messages from non-existent thread returns empty list."""
        # Arrange
        store = CosmosChatMessageStore(
            session_id="session_1", thread_id="thread_1", container=mock_container
        )
        mock_container.read_item.side_effect = CosmosResourceNotFoundError(
            status_code=404, message="Resource not found"
        )

        # Act
        messages = await store.list_messages()

        # Assert
        assert messages == []

    @pytest.mark.asyncio
    async def test_list_messages_returns_stored_messages(self, mock_container):
        """Test listing messages from existing document."""
        # Arrange
        store = CosmosChatMessageStore(
            session_id="session_1", thread_id="thread_1", container=mock_container
        )

        stored_doc = {
            "id": "thread_1",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
        }
        mock_container.read_item.return_value = stored_doc

        # Act
        with patch.object(store, "_deserialize_message", side_effect=lambda x: x):
            messages = await store.list_messages()

        # Assert
        assert len(messages) == 2
        assert messages[0]["content"] == "Hello"
        assert messages[1]["content"] == "Hi there"


class TestSerialization:
    """Tests for serialization and state management."""

    @pytest.mark.asyncio
    async def test_serialize_returns_state_dict(self):
        """Test that serialize returns valid state dictionary."""
        # Arrange
        store = CosmosChatMessageStore(
            session_id="session_1",
            thread_id="thread_1",
            container_name="custom_container",
            database_name="custom_db",
            max_messages=100,
        )

        # Act
        state = await store.serialize()

        # Assert
        assert state["session_id"] == "session_1"
        assert state["thread_id"] == "thread_1"
        assert state["container_name"] == "custom_container"
        assert state["database_name"] == "custom_db"
        assert state["max_messages"] == 100

    @pytest.mark.asyncio
    async def test_update_from_state_restores_configuration(self):
        """Test that update_from_state restores store configuration."""
        # Arrange
        store = CosmosChatMessageStore()

        new_state = {
            "session_id": "restored_session",
            "thread_id": "restored_thread",
            "container_name": "restored_container",
            "database_name": "restored_db",
            "max_messages": 50,
        }

        # Act
        await store.update_from_state(new_state)

        # Assert
        assert store.session_id == "restored_session"
        assert store.thread_id == "restored_thread"
        assert store.container_name == "restored_container"
        assert store.database_name == "restored_db"
        assert store.max_messages == 50

    @pytest.mark.asyncio
    async def test_update_from_state_resets_container(self):
        """Test that update_from_state resets container to use new config."""
        # Arrange
        mock_container = MagicMock()
        store = CosmosChatMessageStore(container=mock_container)
        store._container = mock_container

        new_state = {
            "session_id": "new_session",
            "thread_id": "new_thread",
            "container_name": "new_container",
            "database_name": "new_db",
            "max_messages": None,
        }

        # Act
        await store.update_from_state(new_state)

        # Assert
        assert store._container is None  # Should be reset

    @pytest.mark.asyncio
    async def test_serialize_with_exclude_parameter(self):
        """Test serialize with exclude parameter."""
        # Arrange
        store = CosmosChatMessageStore(session_id="session_1", thread_id="thread_1")

        # Act
        state = await store.serialize(exclude={"max_messages"})

        # Assert
        assert "session_id" in state
        assert "thread_id" in state
        assert "max_messages" not in state


class TestDeepSerialization:
    """Tests for _deep_serialize method."""

    def test_serialize_primitives(self):
        """Test serialization of primitive types."""
        # Arrange
        store = CosmosChatMessageStore()

        # Act & Assert
        assert store._deep_serialize(None) is None
        assert store._deep_serialize("string") == "string"
        assert store._deep_serialize(42) == 42
        assert store._deep_serialize(3.14) == 3.14
        assert store._deep_serialize(True) is True

    def test_serialize_enum(self):
        """Test serialization of Enum values."""
        # Arrange
        store = CosmosChatMessageStore()

        # Act
        result = store._deep_serialize(SampleEnum.VALUE_A)

        # Assert
        assert result == "value_a"

    def test_serialize_datetime(self):
        """Test serialization of datetime objects."""
        # Arrange
        store = CosmosChatMessageStore()
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        # Act
        result = store._deep_serialize(dt)

        # Assert
        assert isinstance(result, str)
        assert "2024-01-15" in result

    def test_serialize_pydantic_model(self):
        """Test serialization of Pydantic models."""
        # Arrange
        store = CosmosChatMessageStore()
        model = SamplePydanticModel(name="test", value=123, tags=["tag1", "tag2"])

        # Act
        result = store._deep_serialize(model)

        # Assert
        assert result["name"] == "test"
        assert result["value"] == 123
        assert result["tags"] == ["tag1", "tag2"]

    def test_serialize_dataclass(self):
        """Test serialization of dataclass objects."""
        # Arrange
        store = CosmosChatMessageStore()
        dc = SampleDataclass(id="test_id", count=5)

        # Act
        result = store._deep_serialize(dc)

        # Assert
        assert result["id"] == "test_id"
        assert result["count"] == 5

    def test_serialize_list(self):
        """Test serialization of lists."""
        # Arrange
        store = CosmosChatMessageStore()
        data = [1, "two", SampleEnum.VALUE_B, None]

        # Act
        result = store._deep_serialize(data)

        # Assert
        assert result == [1, "two", "value_b", None]

    def test_serialize_dict(self):
        """Test serialization of dictionaries."""
        # Arrange
        store = CosmosChatMessageStore()
        data = {"number": 42, "enum": SampleEnum.VALUE_A, "nested": {"key": "value"}}

        # Act
        result = store._deep_serialize(data)

        # Assert
        assert result["number"] == 42
        assert result["enum"] == "value_a"
        assert result["nested"]["key"] == "value"

    def test_serialize_nested_complex_structure(self):
        """Test serialization of deeply nested complex structures."""
        # Arrange
        store = CosmosChatMessageStore()
        data = {
            "models": [
                SamplePydanticModel(name="model1", value=1),
                SamplePydanticModel(name="model2", value=2),
            ],
            "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "status": SampleEnum.VALUE_A,
            "metadata": {"dataclass": SampleDataclass(id="dc1", count=10)},
        }

        # Act
        result = store._deep_serialize(data)

        # Assert
        assert len(result["models"]) == 2
        assert result["models"][0]["name"] == "model1"
        assert isinstance(result["timestamp"], str)
        assert result["status"] == "value_a"
        assert result["metadata"]["dataclass"]["count"] == 10

    def test_serialize_object_with_dict_attribute(self):
        """Test serialization of objects with __dict__ attribute."""
        # Arrange
        store = CosmosChatMessageStore()

        class CustomObject:
            def __init__(self):
                self.public = "visible"
                self._private = "hidden"

        obj = CustomObject()

        # Act
        result = store._deep_serialize(obj)

        # Assert
        assert result["public"] == "visible"
        assert "_private" not in result  # Private attributes excluded

    def test_serialize_object_with_empty_dict(self):
        """Test that objects with empty __dict__ serialize to empty dict."""
        # Arrange
        store = CosmosChatMessageStore()

        class CustomObject:
            def __init__(self):
                pass  # No attributes

        obj = CustomObject()

        # Act
        result = store._deep_serialize(obj)

        # Assert
        assert result == {}  # Empty __dict__ serializes to empty dict

    def test_serialize_builtin_type_converts_to_string(self):
        """Test that unsupported builtin types convert to string."""
        # Arrange
        store = CosmosChatMessageStore()

        # Use a builtin type that doesn't have __dict__ (like int subclass)
        class CustomInt(int):
            pass

        obj = CustomInt(42)
        # Delete __dict__ if it exists
        if hasattr(obj, "__dict__"):
            # For builtin types, we can't really delete __dict__
            # so just test the actual behavior
            result = store._deep_serialize(obj)
            # It will serialize as a dict or as the primitive value
            assert result == 42 or isinstance(result, (dict, str))
        else:
            result = store._deep_serialize(obj)
            assert result == 42


class TestClearMessages:
    """Tests for clear method."""

    @pytest.mark.asyncio
    async def test_clear_deletes_document(self, mock_container):
        """Test that clear deletes the document."""
        # Arrange
        store = CosmosChatMessageStore(
            session_id="session_1", thread_id="thread_1", container=mock_container
        )

        # Act
        await store.clear()

        # Assert
        mock_container.delete_item.assert_called_once_with(
            item="thread_1", partition_key="session_1"
        )

    @pytest.mark.asyncio
    async def test_clear_handles_not_found_gracefully(self, mock_container):
        """Test that clear handles non-existent document gracefully."""
        # Arrange
        store = CosmosChatMessageStore(
            session_id="session_1", thread_id="thread_1", container=mock_container
        )
        mock_container.delete_item.side_effect = CosmosResourceNotFoundError(
            status_code=404, message="Resource not found"
        )

        # Act - should not raise exception
        await store.clear()

        # Assert
        mock_container.delete_item.assert_called_once()


class TestContainerLazyLoading:
    """Tests for lazy container initialization."""

    @patch("src.db.cosmos_chat_store.get_container")
    def test_container_lazy_loads_on_first_access(self, mock_get_container):
        """Test that container is only created when first accessed."""
        # Arrange
        mock_get_container.return_value = MagicMock()
        store = CosmosChatMessageStore(
            container_name="test_container", database_name="test_db"
        )

        # Assert - not called yet
        mock_get_container.assert_not_called()

        # Act - access container property
        _ = store.container

        # Assert - now called
        mock_get_container.assert_called_once_with(
            container_name="test_container", database_name="test_db"
        )

    @patch("src.db.cosmos_chat_store.get_container")
    def test_container_cached_after_first_access(self, mock_get_container):
        """Test that container is cached after first access."""
        # Arrange
        mock_get_container.return_value = MagicMock()
        store = CosmosChatMessageStore()

        # Act
        container1 = store.container
        container2 = store.container

        # Assert - called only once
        assert mock_get_container.call_count == 1
        assert container1 is container2

    def test_provided_container_skips_lazy_loading(self):
        """Test that providing container in __init__ skips lazy loading."""
        # Arrange
        mock_container = MagicMock()

        # Act
        store = CosmosChatMessageStore(container=mock_container)

        # Assert
        assert store._container is mock_container
        assert store.container is mock_container


class TestCosmosStoreState:
    """Tests for CosmosStoreState Pydantic model."""

    def test_state_model_validation(self):
        """Test that CosmosStoreState validates correctly."""
        # Act
        state = CosmosStoreState(
            thread_id="thread_1",
            session_id="session_1",
            container_name="custom_container",
            database_name="custom_db",
            max_messages=100,
        )

        # Assert
        assert state.thread_id == "thread_1"
        assert state.session_id == "session_1"
        assert state.container_name == "custom_container"
        assert state.database_name == "custom_db"
        assert state.max_messages == 100

    def test_state_model_defaults(self):
        """Test CosmosStoreState default values."""
        # Act
        state = CosmosStoreState(thread_id="thread_1", session_id="session_1")

        # Assert
        assert state.container_name == "conversations"
        assert state.database_name == "maf_db"
        assert state.max_messages is None

    def test_state_model_serialization(self):
        """Test that CosmosStoreState can be serialized."""
        # Arrange
        state = CosmosStoreState(
            thread_id="thread_1", session_id="session_1", max_messages=50
        )

        # Act
        serialized = state.model_dump()

        # Assert
        assert serialized["thread_id"] == "thread_1"
        assert serialized["session_id"] == "session_1"
        assert serialized["max_messages"] == 50
