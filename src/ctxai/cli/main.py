import argparse
import logging
import sys


def setup_logging(level: int) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def start_server(args: argparse.Namespace) -> None:
    """Start the CtxAI server."""
    logging.info(f"Starting CtxAI server on {args.host}:{args.port}...")
    # TODO: Import your ASGI/ASGI server module here and run it
    # from ctxai.server import run_server
    # run_server(host=args.host, port=args.port)


def run_agent(args: argparse.Namespace) -> None:
    """Run a specific CtxAI agent."""
    logging.info(f"Running agent '{args.profile}' with task: {args.task}")
    # TODO: Import your core agent orchestration logic here
    # from ctxai.core.agent import run
    # run(profile=args.profile, task=args.task)


def main() -> None:
    parser = argparse.ArgumentParser(description="CtxAI - Dynamic agentic AI framework CLI")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(title="commands", dest="command", required=True)

    # Server command
    server_parser = subparsers.add_parser("server", help="Start the CtxAI API/Web server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    server_parser.set_defaults(func=start_server)

    # Agent tasking command
    agent_parser = subparsers.add_parser("agent", help="Run a CtxAI agent for a specific task")
    agent_parser.add_argument("-p", "--profile", default="default", help="Agent profile to run")
    agent_parser.add_argument("-t", "--task", required=True, help="Task description to process")
    agent_parser.set_defaults(func=run_agent)

    args = parser.parse_args()
    setup_logging(logging.DEBUG if args.debug else logging.INFO)

    try:
        args.func(args)
    except Exception as e:
        logging.error(f"Execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
