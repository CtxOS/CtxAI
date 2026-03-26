from ctxai.helpers import settings
from ctxai.helpers.api import ApiHandler, Request, Response


class ModelConfigGet(ApiHandler):
    """Get current model configuration for chat, utility, and embedding models."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        s = settings.get_settings()

        config = {
            "chat_model": {
                "provider": s.get("chat_model_provider", ""),
                "name": s.get("chat_model_name", ""),
                "api_base": s.get("chat_model_api_base", ""),
                "ctx_length": s.get("chat_model_ctx_length", 0),
                "ctx_history": s.get("chat_model_ctx_history", 0.7),
                "vision": s.get("chat_model_vision", False),
            },
            "utility_model": {
                "provider": s.get("utility_model_provider", ""),
                "name": s.get("utility_model_name", ""),
                "api_base": s.get("utility_model_api_base", ""),
                "ctx_length": s.get("utility_model_ctx_length", 0),
            },
            "embedding_model": {
                "provider": s.get("embedding_model_provider", ""),
                "name": s.get("embedding_model_name", ""),
                "api_base": s.get("embedding_model_api_base", ""),
            },
            "allow_chat_override": s.get("allow_chat_override", True),
        }

        return {"ok": True, "config": config}
