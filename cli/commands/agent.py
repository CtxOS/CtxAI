import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Manage agents")
console = Console()


@app.command("list")
def list_agents():
    """List all available agents"""
    from ctxai.utils import subagents

    with console.status("[bold blue]Fetching agents..."):
        agents = subagents.get_agents_list()

    if not agents:
        console.print("[yellow]No agents found.[/]")
        return

    table = Table(
        title="Available Agents", show_header=True, header_style="bold magenta", border_style="dim"
    )
    table.add_column("Agent", style="cyan", no_wrap=True)
    table.add_column("Role", style="white")
    table.add_column("Status", style="green", justify="center")
    table.add_column("Origin", style="dim yellow")

    for agent in agents:
        status = "running" if agent.enabled else "stopped"
        status_style = "bold green" if agent.enabled else "bold red"
        origins = ", ".join(agent.origin)
        table.add_row(agent.name, agent.title, f"[{status_style}]{status}[/]", origins)

    console.print(table)


@app.command("create")
def create_agent(name: str):
    """Create a new agent"""
    console.print(f"Creating agent: [bold cyan]{name}[/bold cyan]")
    # Implementation placeholder
    console.print("[yellow]Not implemented yet.[/]")


@app.command("remove")
def remove_agent(name: str):
    """Remove an agent"""
    console.print(f"Removing agent: [bold red]{name}[/bold red]")
    # Implementation placeholder
    console.print("[yellow]Not implemented yet.[/]")
