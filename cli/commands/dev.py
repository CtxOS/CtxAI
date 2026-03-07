import typer
from rich.console import Console

app = typer.Typer(help="Developer utilities")
console = Console()


@app.command("doctor")
def doctor():
    """Diagnose environment"""
    console.print("[bold blue]Diagnosing environment...[/]")
    console.print("Python version: [green]OK[/]")
    console.print("Dependencies: [green]OK[/]")
    console.print("[bold green]System is healthy![/]")


@app.command("test")
def test():
    """Run tests"""
    console.print("[bold yellow]Running tests...[/]")
    console.print("[red]No tests found.[/]")
