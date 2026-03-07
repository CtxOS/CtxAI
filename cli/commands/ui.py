import typer

app = typer.Typer(help="Manage Web UI")


@app.command("start")
def start_ui():
    """Start the CtxAI Web UI"""
    # Load env and initialize
    from cli import ui as ui_module
    from ctxai.core import runtime
    from ctxai.utils import dotenv

    runtime.initialize()
    dotenv.load_dotenv()
    ui_module.run()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Start the Web UI by default if no subcommand is provided"""
    if ctx.invoked_subcommand is None:
        start_ui()
