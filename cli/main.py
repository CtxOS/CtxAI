import typer
from rich.console import Console

app = typer.Typer(
    name="ctxai",
    help="CtxAI — Autonomous Agent Platform",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()

# We still have to import the Typer objects to register them
from cli.commands import agent, dev, ui

# Core Commands
app.add_typer(ui.app, name="ui", rich_help_panel="Core Commands")
app.add_typer(agent.app, name="agent", rich_help_panel="Core Commands")

# Development
app.add_typer(dev.app, name="dev", rich_help_panel="Development")


# Placeholders
@app.command("chat", help="Manage chats", rich_help_panel="Core Commands")
def chat_placeholder():
    console.print("[yellow]Chat management coming soon...[/]")


@app.command("plugin", help="Manage plugins", rich_help_panel="Core Commands")
def plugin_placeholder():
    console.print("[yellow]Plugin management coming soon...[/]")


@app.command("skill", help="Manage skills", rich_help_panel="Core Commands")
def skill_placeholder():
    console.print("[yellow]Skill management coming soon...[/]")


@app.command("project", help="Manage projects", rich_help_panel="Core Commands")
def project_placeholder():
    console.print("[yellow]Project management coming soon...[/]")


@app.command("server", help="Control runtime server", rich_help_panel="Core Commands")
def server_placeholder():
    console.print("[yellow]Server control coming soon...[/]")


@app.command("tunnel", help="Manage tunnels", rich_help_panel="Core Commands")
def tunnel_placeholder():
    console.print("[yellow]Tunnel management coming soon...[/]")


@app.command("test", help="Run tests", rich_help_panel="Development")
def test_placeholder():
    console.print("[yellow]Test runner coming soon...[/]")


@app.command("doctor", help="Diagnose environment", rich_help_panel="Development")
def doctor_placeholder():
    console.print("[yellow]Doctor utility coming soon...[/]")


@app.command("logs", help="View logs", rich_help_panel="Development")
def logs_placeholder():
    console.print("[yellow]Log viewer coming soon...[/]")


@app.command("backup", help="Backup / restore data", rich_help_panel="Data & System")
def backup_placeholder():
    console.print("[yellow]Backup utilities coming soon...[/]")


@app.command("config", help="Manage configuration", rich_help_panel="Data & System")
def config_placeholder():
    console.print("[yellow]Configuration management coming soon...[/]")


@app.command("cache", help="Manage cache", rich_help_panel="Data & System")
def cache_placeholder():
    console.print("[yellow]Cache management coming soon...[/]")


@app.command("reset", help="Reset runtime state", rich_help_panel="Data & System")
def reset_placeholder():
    console.print("[yellow]Reset utilities coming soon...[/]")


@app.command("completion", help="Generate shell completion", rich_help_panel="Other")
def completion_placeholder():
    console.print("[yellow]Completion generation coming soon...[/]")


@app.command("version", help="Show version", rich_help_panel="Other")
def version():
    """Show version"""
    console.print("CtxAI version: [bold cyan]0.1.0[/bold cyan]")


def main():
    app()


if __name__ == "__main__":
    main()
