# Contributing to Ctx AI

Thank you for your interest in contributing! We welcome bug fixes, new features, docs improvements, and tests.

## How to contribute

1. Fork the repository and clone your fork.
2. Create a branch with a descriptive name: `git checkout -b feature/my-feature`.
3. Run tests locally: `uv run pytest -q`.
4. Run lints: `uv run ruff check src/ctxai tests`.
5. Open a pull request against `main`.

## Issue process

- Use the issue templates for bug reports, feature requests, or questions.
- Include clear reproduction steps and expected behavior.

## Pull request process

- Link your PR to an issue when possible.
- Keep PRs focused and atomic.
- Add tests for new behavior.
- Ensure CI passes.

## Labels and project triage

We use labels such as `area:api`, `area:plugins`, `type:bug`, `type:enhancement`, `status:needs triage`, and `status:ready`.

## Code style

- Python formatting + linting: `uv run ruff format . && uv run ruff check .`
- Type checking: `uv run mypy src/ctxai --ignore-missing-imports`

## Community Conduct

Please follow our [Code of Conduct](./CODE_OF_CONDUCT.md).
