"""
Cosmos DB Chat Message Store

Implementation of ChatMessageStore protocol for Agent Framework,
using Cosmos DB for persistent storage.

NOTE: This implementation only saves chat messages to Cosmos DB.
Loading chat history on page refresh is NOT implemented because
CopilotKit does not support restoring conversation state from backend.
The data is stored and can be used for analytics, admin dashboards, etc.
If you need to load history, you can implement a REST API to fetch it.
"""

from collections.abc import Sequence
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone
from enum import Enum
from dataclasses import is_dataclass, asdict
from pydantic import BaseModel
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from agent_framework import ChatMessage
from .cosmos import get_container


class CosmosStoreState(BaseModel):
    """State model for serializing and deserializing Cosmos DB chat message store data."""

    thread_id: str
    session_id: str
    container_name: str = "conversations"
    database_name: str = "maf_db"
    max_messages: int | None = None


class CosmosChatMessageStore:
    """Cosmos DB-backed implementation of ChatMessageStore for Agent Framework.

    Stores chat messages in Cosmos DB with automatic persistence across sessions.
    Compatible with Agent Framework's chat_message_store_factory pattern.
    """

    def __init__(
        self,
        session_id: str | None = None,
        thread_id: str | None = None,
        container_name: str = "conversations",
        database_name: str = "maf_db",
        max_messages: int | None = None,
        container: ContainerProxy | None = None,
    ) -> None:
        """Initialize the Cosmos DB chat message store.

        Args:
            session_id: Session identifier (partition key). Auto-generated if not provided.
            thread_id: Unique identifier for this conversation thread. Auto-generated if not provided.
            container_name: Cosmos DB container name (default: conversations).
            database_name: Cosmos DB database name (default: maf_db).
            max_messages: Maximum number of messages to retain. When exceeded, oldest messages are trimmed.
            container: Optional pre-configured Cosmos DB container.
        """
        self.session_id = session_id or f"session_{uuid4()}"
        self.thread_id = thread_id or f"thread_{uuid4()}"
        self.container_name = container_name
        self.database_name = database_name
        self.max_messages = max_messages
        self._container = container

    @property
    def container(self) -> ContainerProxy:
        """Get the Cosmos DB container (lazy initialization)."""
        if self._container is None:
            self._container = get_container(
                container_name=self.container_name,
                database_name=self.database_name,
            )
        return self._container

    @property
    def document_id(self) -> str:
        """Get the Cosmos DB document ID for this thread."""
        return self.thread_id

    async def add_messages(self, messages: Sequence[ChatMessage]) -> None:
        """Add messages to the Cosmos DB store.

        Args:
            messages: Sequence of ChatMessage objects to add to the store.
        """
        if not messages:
            return

        # Get or create document
        try:
            doc = self.container.read_item(
                item=self.document_id,
                partition_key=self.session_id,
            )
        except CosmosResourceNotFoundError:
            # Create new document
            doc = {
                "id": self.document_id,
                "session_id": self.session_id,
                "thread_id": self.thread_id,
                "messages": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

        # Append new messages
        serialized_messages = [self._serialize_message(msg) for msg in messages]
        doc["messages"].extend(serialized_messages)
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Apply message limit if configured
        if self.max_messages is not None and len(doc["messages"]) > self.max_messages:
            # Keep only the most recent max_messages
            doc["messages"] = doc["messages"][-self.max_messages :]

        # Upsert document
        self.container.upsert_item(body=doc)

    async def list_messages(self) -> list[ChatMessage]:
        """Get all messages from the store in chronological order.

        Returns:
            List of ChatMessage objects in chronological order (oldest first).
        """
        try:
            doc = self.container.read_item(
                item=self.document_id,
                partition_key=self.session_id,
            )
            messages = []
            for serialized_message in doc.get("messages", []):
                message = self._deserialize_message(serialized_message)
                messages.append(message)
            return messages
        except CosmosResourceNotFoundError:
            # No messages yet
            return []

    async def serialize(self, **kwargs: Any) -> Any:
        """Serialize the current store state for persistence.

        Implements ChatMessageStoreProtocol.serialize().

        Returns:
            Dictionary containing serialized store configuration.
        """
        state = CosmosStoreState(
            thread_id=self.thread_id,
            session_id=self.session_id,
            container_name=self.container_name,
            database_name=self.database_name,
            max_messages=self.max_messages,
        )
        return state.model_dump(**kwargs)

    async def update_from_state(
        self, serialized_store_state: Any, **kwargs: Any
    ) -> None:
        """Update store from serialized state.

        Implements ChatMessageStoreProtocol.update_from_state().

        Args:
            serialized_store_state: Previously serialized state data.
            **kwargs: Additional arguments for deserialization.
        """
        if serialized_store_state:
            state = CosmosStoreState.model_validate(serialized_store_state, **kwargs)
            self.thread_id = state.thread_id
            self.session_id = state.session_id
            self.container_name = state.container_name
            self.database_name = state.database_name
            self.max_messages = state.max_messages

            # Reset container to use new config
            self._container = None

    def _deep_serialize(self, obj: Any) -> Any:
        """Recursively serialize any object to JSON-compatible types.

        Handles: Enum, Pydantic models, dataclasses, datetime, lists, dicts, and primitives.
        """
        # None and primitives
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj

        # Enum - convert to value
        if isinstance(obj, Enum):
            return obj.value

        # datetime - convert to ISO string
        if isinstance(obj, datetime):
            return obj.isoformat()

        # Pydantic model
        if hasattr(obj, "model_dump"):
            return self._deep_serialize(obj.model_dump())
        if hasattr(obj, "dict"):
            return self._deep_serialize(obj.dict())

        # dataclass
        if is_dataclass(obj) and not isinstance(obj, type):
            return self._deep_serialize(asdict(obj))

        # List/tuple - recursively serialize each element
        if isinstance(obj, (list, tuple)):
            return [self._deep_serialize(item) for item in obj]

        # Dict - recursively serialize each value
        if isinstance(obj, dict):
            return {k: self._deep_serialize(v) for k, v in obj.items()}

        # Objects with __dict__ (generic objects)
        if hasattr(obj, "__dict__"):
            return self._deep_serialize(
                {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
            )

        # Fallback: convert to string
        return str(obj)

    def _serialize_message(self, message: ChatMessage) -> dict:
        """Serialize a ChatMessage to dictionary.

        Args:
            message: ChatMessage instance to serialize.

        Returns:
            Dictionary representation of the message.
        """
        return self._deep_serialize(message)

    def _deserialize_message(self, serialized_message: dict) -> ChatMessage:
        """Deserialize a dictionary to ChatMessage.

        Args:
            serialized_message: Dictionary representation of a message.

        Returns:
            ChatMessage instance.
        """
        # Try different deserialization methods
        if hasattr(ChatMessage, "model_validate"):
            return ChatMessage.model_validate(serialized_message)
        elif hasattr(ChatMessage, "parse_obj"):
            return ChatMessage.parse_obj(serialized_message)
        else:
            # Fallback: direct instantiation
            return ChatMessage(**serialized_message)

    async def clear(self) -> None:
        """Remove all messages from the store by deleting the document."""
        try:
            self.container.delete_item(
                item=self.document_id,
                partition_key=self.session_id,
            )
        except CosmosResourceNotFoundError:
            pass  # Already deleted or never created
