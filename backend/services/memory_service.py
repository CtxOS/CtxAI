"""
Memory service for managing memory operations.
"""

from datetime import datetime
from typing import Any


class MemoryService:
    """Service for managing memory operations."""

    def __init__(self):
        self._memories: dict[str, dict[str, Any]] = {}

    def create_memory(self, content: str, tags: list[str] = None, agent_id: str = None) -> str:
        """Create a new memory."""
        memory_id = f"memory_{len(self._memories) + 1}"
        self._memories[memory_id] = {
            "id": memory_id,
            "content": content,
            "tags": tags or [],
            "agent_id": agent_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        return memory_id

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Get a memory by ID."""
        return self._memories.get(memory_id)

    def search_memories(self, query: str, agent_id: str = None) -> list[dict[str, Any]]:
        """Search memories by content."""
        results = []
        query_lower = query.lower()

        for memory in self._memories.values():
            if agent_id and memory["agent_id"] != agent_id:
                continue

            if query_lower in memory["content"].lower():
                results.append(memory)

        return results

    def list_memories(self, agent_id: str = None, tags: list[str] = None) -> list[dict[str, Any]]:
        """List memories, optionally filtered."""
        memories = list(self._memories.values())

        if agent_id:
            memories = [m for m in memories if m["agent_id"] == agent_id]

        if tags:
            memories = [m for m in memories if any(tag in m["tags"] for tag in tags)]

        return memories

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False
