from typing import Any

from ctxai.agent import AgentContext
from ctxai.helpers.api import ApiHandler
from ctxai.helpers.flask_compat import Response


class NotificationsHistory(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    async def process(self, input: dict, request: Any) -> dict | Response:
        # Get the global notification manager
        notification_manager = AgentContext.get_notification_manager()

        # Return all notifications for history modal
        notifications = notification_manager.output_all()
        return {
            "notifications": notifications,
            "guid": notification_manager.guid,
            "count": len(notifications),
        }
