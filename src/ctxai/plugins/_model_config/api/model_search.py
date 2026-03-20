from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Request
from ctxai.helpers.api import Response
from ctxai.helpers.providers import get_providers


class ModelSearch(ApiHandler):
    """Search available models by provider or name filter."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        model_type = input.get("type", "chat")  # chat, embedding
        query = input.get("query", "").lower()

        providers = get_providers(model_type)

        results: list[dict] = []
        for provider in providers:
            provider_name = provider.get("value", "")
            provider_label = provider.get("label", provider_name)

            if query and query not in provider_name.lower() and query not in provider_label.lower():
                continue

            results.append(
                {
                    "provider": provider_name,
                    "label": provider_label,
                },
            )

        return {"ok": True, "type": model_type, "results": results}
