"""
Chat service for managing chat operations.
"""

from datetime import datetime
from typing import Any


class ChatService:
    """Service for managing chat operations."""

    def __init__(self):
        self._chats: dict[str, dict[str, Any]] = {}

    def create_chat(self, agent_id: str, title: str = None) -> str:
        """Create a new chat session."""
        chat_id = f"chat_{len(self._chats) + 1}"
        self._chats[chat_id] = {
            "id": chat_id,
            "agent_id": agent_id,
            "title": title or f"Chat {chat_id}",
            "messages": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        return chat_id

    def get_chat(self, chat_id: str) -> dict[str, Any] | None:
        """Get a chat by ID."""
        return self._chats.get(chat_id)

    def add_message(self, chat_id: str, message: dict[str, Any]) -> bool:
        """Add a message to a chat."""
        if chat_id in self._chats:
            self._chats[chat_id]["messages"].append(message)
            self._chats[chat_id]["updated_at"] = datetime.now()
            return True
        return False

    def list_chats(self, agent_id: str = None) -> list[dict[str, Any]]:
        """List chats, optionally filtered by agent."""
        chats = list(self._chats.values())
        if agent_id:
            chats = [chat for chat in chats if chat["agent_id"] == agent_id]
        return chats

    def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat."""
        if chat_id in self._chats:
            del self._chats[chat_id]
            return True
        return False
