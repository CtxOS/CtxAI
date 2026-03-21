from typing import Any

from ctxai.agent import AgentContext
from ctxai.helpers.api import ApiHandler
from ctxai.helpers.flask_compat import Response


class NotificationsClear(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    async def process(self, input: dict, request: Any) -> dict | Response:
        # Get the global notification manager
        notification_manager = AgentContext.get_notification_manager()

        # Clear all notifications
        notification_manager.clear_all()

        return {"success": True, "message": "All notifications cleared"}
