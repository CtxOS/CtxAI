"""
Skill service for managing skill operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class SkillService:
    """Service for managing skill operations."""

    def __init__(self):
        self._skills: Dict[str, Dict[str, Any]] = {}

    def create_skill(self, name: str, description: str, code: str, category: str = "custom") -> str:
        """Create a new skill."""
        skill_id = f"skill_{len(self._skills) + 1}"
        self._skills[skill_id] = {
            "id": skill_id,
            "name": name,
            "description": description,
            "code": code,
            "category": category,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "enabled": True,
        }
        return skill_id

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get a skill by ID."""
        return self._skills.get(skill_id)

    def list_skills(self, category: str = None, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List skills, optionally filtered."""
        skills = list(self._skills.values())

        if category:
            skills = [s for s in skills if s["category"] == category]

        if enabled_only:
            skills = [s for s in skills if s["enabled"]]

        return skills

    def update_skill(self, skill_id: str, updates: Dict[str, Any]) -> bool:
        """Update a skill."""
        if skill_id in self._skills:
            self._skills[skill_id].update(updates)
            self._skills[skill_id]["updated_at"] = datetime.now()
            return True
        return False

    def delete_skill(self, skill_id: str) -> bool:
        """Delete a skill."""
        if skill_id in self._skills:
            del self._skills[skill_id]
            return True
        return False
