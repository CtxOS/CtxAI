import argparse
import sys
import os
from ctxai import initialize
from ctxai import agent
from ctxai.helpers import runtime, dotenv, print_style
from ctxai.helpers.print_style import PrintStyle

def cmd_start(args):
    """Start the Web UI."""
    from ctxai import run_ui
    runtime.initialize()
    dotenv.load_dotenv()
    run_ui.run()

def cmd_run(args):
    """Run a single prompt in the terminal."""
    runtime.initialize()
    dotenv.load_dotenv()
    
    config = initialize.initialize_agent()
    context = agent.AgentContext(config=config, set_current=True)
    
    PrintStyle().print(f"Agent initialized. Running prompt: {args.prompt}")
    
    async def run_async():
        response = await context.agent0.monologue()
        PrintStyle().print(f"\nResponse: {response}")

    import asyncio
    asyncio.run(run_async())

def cmd_version(args):
    """Print the version."""
    from ctxai.helpers import git
    try:
        info = git.get_git_info()
        print(f"CtxAI version: {info.get('version', '0.1.0')}")
    except Exception:
        print("CtxAI version: 0.1.0 (dev)")

def main():
    parser = argparse.ArgumentParser(prog="ctxai", description="CtxAI CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # start
    start_parser = subparsers.add_parser("start", help="Start Web UI")
    start_parser.add_argument("--port", type=int, help="Port to run on")
    start_parser.add_argument("--host", type=str, help="Host to run on")
    start_parser.set_defaults(func=cmd_start)

    # run
    run_parser = subparsers.add_parser("run", help="Run a prompt")
    run_parser.add_argument("prompt", type=str, help="Prompt to run")
    run_parser.set_defaults(func=cmd_run)

    # version
    version_parser = subparsers.add_parser("version", help="Show version")
    version_parser.set_defaults(func=cmd_version)

    args = parser.parse_known_args()[0]
    
    if args.command:
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
