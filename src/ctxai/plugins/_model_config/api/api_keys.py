from ctxai.helpers import settings
from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Request
from ctxai.helpers.api import Response


class GetApiKeys(ApiHandler):
    """Get stored API keys (masked) for all providers."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        s = settings.get_settings()
        api_keys: dict[str, str] = s.get("api_keys", {})

        # Return masked keys — first 4 + last 4 chars
        masked: dict[str, str] = {}
        for provider, key in api_keys.items():
            if key and len(key) > 12:
                masked[provider] = key[:4] + "..." + key[-4:]
            elif key:
                masked[provider] = key[:4] + "..."
            else:
                masked[provider] = ""

        return {"ok": True, "api_keys": masked}
