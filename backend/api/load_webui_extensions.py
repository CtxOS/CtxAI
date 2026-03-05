from backend.utils import plugins
from backend.utils.api import ApiHandler, Request, Response


class LoadWebuiExtensions(ApiHandler):
    """
    API endpoint for Welcome Screen banners.
    Add checks as extension scripts in backend/extensions/banners/ or usr/extensions/banners/
    """

    async def process(self, input: dict, request: Request) -> dict | Response:
        extension_point = input.get("extension_point", [])
        filters = input.get("filters", [])

        if not extension_point:
            return Response(status=400, response="Missing extension_point")

        exts = plugins.get_webui_extensions(
            agent=None, extension_point=extension_point, filters=filters
        )

        return {"extensions": exts or []}
