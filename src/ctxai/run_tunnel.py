import asyncio

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ctxai.api.tunnel import Tunnel, stop
from ctxai.helpers import dotenv, process, runtime
from ctxai.helpers.print_style import PrintStyle

lock = asyncio.Lock()


async def handle_request(request: Request):
    body = await request.json()
    tunnel = Tunnel(None, lock)
    result = await tunnel.handle_request(request=type("Req", (), {"json": lambda self: body})())
    if isinstance(result, dict):
        return JSONResponse(result)
    return JSONResponse({"error": "Unexpected response"}, status_code=500)


app = Starlette(routes=[Route("/", handle_request, methods=["POST"])])


def run():
    import uvicorn

    PrintStyle().print("Starting tunnel server...")

    tunnel_api_port = runtime.get_tunnel_api_port()
    host = runtime.get_arg("host") or dotenv.get_dotenv_value("WEB_UI_HOST") or "localhost"

    config = uvicorn.Config(app, host=host, port=tunnel_api_port, log_level="warning")
    server = uvicorn.Server(config)

    process.set_server(server)

    try:
        server.run()
    finally:
        stop()


# run the internal server
if __name__ == "__main__":
    runtime.initialize()
    dotenv.load_dotenv()
    run()
