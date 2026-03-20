from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Request
from ctxai.helpers.api import session


class ApiLogout(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict:
        try:
            session.clear()
        except Exception:
            session.pop("authentication", None)
            session.pop("csrf_token", None)
        return {"ok": True}
