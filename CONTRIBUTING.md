# Contributing to agent-replay

Thank you for your interest in contributing!

## Quick start

```bash
git clone https://github.com/routsom/agent-replay
cd agent-replay
pip install -e ".[dev]"
```

## Before submitting a PR

Run the full check suite — all three must pass with zero errors:

```bash
pytest tests/ -v
mypy agent_replay/ --strict
ruff check agent_replay/
```

## Branch naming

- `feat/<short-slug>` — new feature
- `fix/<short-slug>` — bug fix
- `chore/<short-slug>` — tooling, docs, CI

## What belongs in a PR

- Every feature branch must include tests before merge
- Update `CHANGELOG.md` under an `[Unreleased]` section
- Update `docs/` if the public API or CLI changes
- Keep commits conventional: `feat:`, `fix:`, `docs:`, `test:`, `chore:`

## Adding a new provider integration

1. Create `agent_replay/integrations/<provider>.py`
2. Add pricing entries to `pricing/models.yaml` and bump `version`
3. Add an example in `examples/`
4. Add an integration test in `tests/integration/`
5. Document in `docs/integrations.md`

## Adding a new CLI subcommand

1. Create `agent_replay/cli/cmd_<name>.py` with a Typer `app`
2. Register it in `agent_replay/cli/main.py`
3. Add a `--json` flag if the command returns structured data
4. Write at least one CLI integration test using `typer.testing.CliRunner`

## Core principles (non-negotiable)

- **Never raise from tracing code into user code** — all store/recorder ops must be wrapped in `try/except`
- **No ORM, no web server, no async in the core** — keep it stdlib + SQLite
- **IDs are UUID4** — never sequential integers
- **Store raw provider responses** — don't normalize inputs/outputs

## Reporting bugs

Open an issue at https://github.com/routsom/agent-replay/issues with:
- Python version and OS
- Minimal reproduction script
- Full traceback
