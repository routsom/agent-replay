# CLAUDE.md — agent-replay

> Instructions for Claude Code working on this repository.
> Read this entire file before touching any code.

---

## Project Overview

**agent-replay** is a dead-simple, local-first, framework-agnostic agent
observability library. It records every step of an AI agent run — tool calls,
reasoning, token usage, latency, costs — to a portable SQLite database, and
lets you replay, diff, and annotate those runs from a CLI.

**North star:** a developer should be able to add one decorator and get full
agent tracing with zero infrastructure. No server. No cloud account. One file
on disk.

### Core value propositions
- **Zero server** — one SQLite file, runs anywhere
- **Framework agnostic** — wraps LangGraph, Google ADK, CrewAI, raw
  Anthropic/OpenAI SDKs, and anything else via a thin protocol
- **Replay** — re-run a recorded trace against a new model or prompt, then
  diff the outputs side-by-side
- **Cost tracking** — per-step and per-run token cost across all major
  providers, using a live pricing manifest
- **Annotate** — attach human notes and pass/fail verdicts to any run or step,
  building an eval dataset over time

---

## Repository Layout

```
agent-replay/
├── CLAUDE.md                   ← you are here
├── README.md
├── pyproject.toml              ← Python package (primary SDK)
├── package.json                ← TypeScript SDK (secondary)
├── tsconfig.json
│
├── agent_replay/               ← Python package root
│   ├── __init__.py             ← public API surface
│   ├── recorder.py             ← core Recorder class
│   ├── session.py              ← Session + Step data models (dataclasses)
│   ├── store.py                ← SQLite persistence layer
│   ├── replay.py               ← Replay engine
│   ├── diff.py                 ← Diff engine
│   ├── cost.py                 ← Token cost calculator
│   ├── pricing.py              ← Pricing manifest loader (YAML → dict)
│   ├── export.py               ← JSONL / HTML report export
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py             ← Typer CLI entry point
│   │   ├── cmd_record.py       ← `agent-replay record` subcommand
│   │   ├── cmd_show.py         ← `agent-replay show`
│   │   ├── cmd_list.py         ← `agent-replay list`
│   │   ├── cmd_diff.py         ← `agent-replay diff`
│   │   ├── cmd_annotate.py     ← `agent-replay annotate`
│   │   └── cmd_export.py       ← `agent-replay export`
│   └── integrations/
│       ├── __init__.py
│       ├── anthropic.py        ← Anthropic SDK wrapper
│       ├── openai.py           ← OpenAI SDK wrapper
│       ├── langchain.py        ← LangChain callback handler
│       ├── google_adk.py       ← Google ADK integration
│       └── crewai.py           ← CrewAI integration
│
├── ts/                         ← TypeScript SDK
│   ├── src/
│   │   ├── index.ts
│   │   ├── recorder.ts
│   │   ├── session.ts
│   │   ├── store.ts            ← better-sqlite3 persistence
│   │   ├── cost.ts
│   │   └── integrations/
│   │       ├── anthropic.ts
│   │       └── openai.ts
│   └── tsconfig.json
│
├── pricing/
│   └── models.yaml             ← provider/model pricing manifest
│
├── tests/
│   ├── unit/
│   │   ├── test_recorder.py
│   │   ├── test_store.py
│   │   ├── test_cost.py
│   │   ├── test_diff.py
│   │   └── test_replay.py
│   ├── integration/
│   │   ├── test_anthropic_integration.py
│   │   └── test_cli.py
│   └── fixtures/
│       └── sample_session.json ← golden fixture for diff/replay tests
│
├── docs/
│   ├── quickstart.md
│   ├── integrations.md
│   ├── schema.md               ← SQLite schema reference
│   └── pricing.md
│
└── examples/
    ├── basic_anthropic.py
    ├── langchain_agent.py
    ├── google_adk_agent.py
    └── typescript_example.ts
```

---

## Data Model

These are the canonical types. Keep them stable — everything else depends on
them. If you need to change a field, add a migration in `store.py`, never
rename silently.

### Session
```python
@dataclass
class Session:
    id: str                   # UUID4, generated at record start
    name: str | None          # optional human label
    framework: str            # "anthropic" | "openai" | "langchain" | "google_adk" | "crewai" | "custom"
    model: str                # e.g. "claude-sonnet-4-6"
    started_at: datetime
    ended_at: datetime | None
    status: str               # "running" | "completed" | "error"
    tags: list[str]           # free-form for filtering
    metadata: dict            # arbitrary key-value, JSON-stored
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    steps: list[Step]         # populated on read, not stored inline
```

### Step
```python
@dataclass
class Step:
    id: str                   # UUID4
    session_id: str
    sequence: int             # 0-indexed order within session
    type: str                 # "llm_call" | "tool_call" | "tool_result" | "reasoning" | "message"
    started_at: datetime
    ended_at: datetime | None
    latency_ms: int | None
    input: dict               # raw input (prompt, tool args, etc.)
    output: dict              # raw output (response, tool result, etc.)
    input_tokens: int
    output_tokens: int
    cost_usd: float
    error: str | None         # exception message if step failed
    annotation: str | None    # human note attached via `annotate`
    verdict: str | None       # "pass" | "fail" | None
```

### DiffResult
```python
@dataclass
class DiffResult:
    session_a: str            # session ID
    session_b: str
    steps_added: list[Step]   # in B but not A
    steps_removed: list[Step] # in A but not B
    steps_changed: list[tuple[Step, Step]]  # (a_step, b_step) pairs that differ
    cost_delta_usd: float
    token_delta: int
    summary: str              # human-readable one-liner
```

---

## SQLite Schema

The database file defaults to `~/.agent-replay/replay.db`. Users can override
via `AGENT_REPLAY_DB` env var or `--db` CLI flag.

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    name TEXT,
    framework TEXT NOT NULL,
    model TEXT NOT NULL,
    started_at TEXT NOT NULL,    -- ISO-8601
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    tags TEXT NOT NULL DEFAULT '[]',   -- JSON array
    metadata TEXT NOT NULL DEFAULT '{}',
    total_input_tokens INTEGER NOT NULL DEFAULT 0,
    total_output_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost_usd REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE steps (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    latency_ms INTEGER,
    input TEXT NOT NULL DEFAULT '{}',   -- JSON
    output TEXT NOT NULL DEFAULT '{}',  -- JSON
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    error TEXT,
    annotation TEXT,
    verdict TEXT
);

CREATE INDEX idx_steps_session ON steps(session_id, sequence);
CREATE INDEX idx_sessions_framework ON sessions(framework);
CREATE INDEX idx_sessions_started ON sessions(started_at);
```

Schema migrations live in `store.py` as a versioned list of SQL strings,
applied on connection if `PRAGMA user_version` is behind. Never use Alembic —
keep it simple.

---

## Pricing Manifest

`pricing/models.yaml` is the single source of truth for cost calculation.

```yaml
# pricing/models.yaml
version: "2026-05"
providers:
  anthropic:
    claude-opus-4-6:
      input_per_million: 15.00
      output_per_million: 75.00
    claude-sonnet-4-6:
      input_per_million: 3.00
      output_per_million: 15.00
    claude-haiku-4-5-20251001:
      input_per_million: 0.80
      output_per_million: 4.00
  openai:
    gpt-4o:
      input_per_million: 2.50
      output_per_million: 10.00
    gpt-4o-mini:
      input_per_million: 0.15
      output_per_million: 0.60
  google:
    gemini-2.0-flash-exp:
      input_per_million: 0.075
      output_per_million: 0.30
```

`cost.py` loads this manifest and exposes `calculate_cost(model, provider,
input_tokens, output_tokens) -> float`. If a model is not in the manifest,
log a warning and return `0.0` — never raise.

---

## Core API (Python)

The public surface is minimal. If it's not in `__init__.py`, it's internal.

### Decorator pattern (simplest)

```python
from agent_replay import record

@record(name="my-agent-run", tags=["prod", "v2"])
def run_my_agent(prompt: str) -> str:
    # your agent code here
    ...
```

### Context manager (explicit)

```python
from agent_replay import Recorder

with Recorder(name="my-run", framework="anthropic") as r:
    step = r.step("llm_call", input={"prompt": prompt})
    response = client.messages.create(...)
    step.finish(output={"text": response.content[0].text},
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens)
```

### Anthropic integration (drop-in)

```python
from anthropic import Anthropic
from agent_replay.integrations.anthropic import ReplayClient

client = ReplayClient(Anthropic(), session_name="customer-support")
# use client exactly like Anthropic() — tracing is automatic
response = client.messages.create(model="claude-sonnet-4-6", ...)
```

---

## CLI Reference

All subcommands accept `--db <path>` to override the database location.

```
agent-replay list [--limit 20] [--tag prod] [--framework anthropic]
    List recent sessions in a table (id, name, model, steps, cost, status)

agent-replay show <session-id> [--steps] [--json]
    Show full detail for a session. --steps prints each step.
    --json emits raw JSON for piping.

agent-replay diff <session-id-a> <session-id-b> [--json]
    Side-by-side diff of two runs. Highlights added/removed/changed steps,
    cost delta, and token delta.

agent-replay replay <session-id> [--model <override>] [--dry-run]
    Re-execute a recorded session against a (possibly different) model.
    Saves the result as a new session linked to the original via metadata.
    --dry-run prints the plan without executing.

agent-replay annotate <session-id> [--step <step-id>] --note "text" [--verdict pass|fail]
    Attach a human note and optional verdict to a session or individual step.

agent-replay export <session-id> --format jsonl|html [--out <file>]
    Export a session. JSONL is one JSON object per step. HTML is a self-
    contained report with syntax-highlighted inputs/outputs.

agent-replay stats [--days 7]
    Aggregate cost and token usage across recent sessions.
```

---

## TypeScript SDK

The TS SDK mirrors the Python API. Use `better-sqlite3` (synchronous) — not
`sql.js`. The TS SDK is secondary; keep it in sync with Python but don't
gold-plate it in v1.

```typescript
import { Recorder } from 'agent-replay'
import Anthropic from '@anthropic-ai/sdk'

const recorder = new Recorder({ name: 'my-run', framework: 'anthropic' })
const session = await recorder.start()

const step = session.step('llm_call', { prompt })
const response = await client.messages.create({ ... })
await step.finish({
  output: { text: response.content[0].text },
  inputTokens: response.usage.input_tokens,
  outputTokens: response.usage.output_tokens,
})

await session.end()
```

---

## Engineering Principles

### 1. Never break the zero-infrastructure promise
The library must work with `pip install agent-replay` and nothing else. No
Docker. No Redis. No Postgres. No cloud credentials. SQLite is the only
runtime dependency beyond Python stdlib.

### 2. Fail silently in production
If recording fails for any reason (disk full, permissions, corrupt DB), catch
the exception, log a warning to stderr, and let the agent continue. **Never
raise from tracing code into user code.** Tracing is never load-bearing.

```python
# CORRECT
try:
    self._store.save_step(step)
except Exception as e:
    logger.warning(f"agent-replay: failed to save step: {e}")

# WRONG — breaks the user's agent
self._store.save_step(step)  # raises, kills the run
```

### 3. Inputs and outputs are stored as raw dicts
Don't normalise or transform what goes in. Store the raw provider response.
This preserves fidelity for replay and diff. Serialise with `json.dumps` using
`default=str` for datetimes and unknown types.

### 4. IDs are UUID4, never sequential integers
Sequential IDs reveal record counts and create merge conflicts when users sync
databases. Always `import uuid; uuid.uuid4()`.

### 5. No ORM
Use raw `sqlite3` with parameterised queries. No SQLAlchemy. No Tortoise. The
schema is simple enough that an ORM adds more complexity than it removes.

### 6. Type everything in Python
Use dataclasses and `typing` annotations throughout. The project targets
Python 3.11+. Use `|` union syntax, not `Optional[X]`.

### 7. CLi output is human-first, `--json` is machine-first
Default output is a readable table or formatted text (use `rich` for tables
and syntax highlighting). When `--json` is passed, emit clean JSON to stdout
with no extra decoration — suitable for piping.

---

## Testing Rules

- **Unit tests** cover all of: `recorder.py`, `store.py`, `cost.py`,
  `diff.py`. Aim for >90% coverage on these four files.
- **Integration tests** use a real in-memory SQLite (`:memory:`) — not mocks
  of the store. Mock only external LLM API calls.
- **Never hit a live LLM API in tests.** Use `pytest-recording` (cassette
  mode) or `unittest.mock.patch` for all provider calls.
- **Golden fixtures** in `tests/fixtures/` are the source of truth for diff
  and replay output. If you change diff output format, regenerate and commit
  the fixture.
- Every PR must pass `pytest` and `mypy --strict` with zero errors.

Run tests:
```bash
pytest tests/ -v
mypy agent_replay/ --strict
ruff check agent_replay/
```

---

## Common Tasks

### Adding a new provider integration

1. Create `agent_replay/integrations/<provider>.py`
2. Implement a wrapper class that intercepts API calls and calls
   `recorder.step(...)` / `step.finish(...)`
3. Add pricing entries to `pricing/models.yaml`
4. Add at least one example in `examples/`
5. Add an integration test in `tests/integration/`
6. Document in `docs/integrations.md`

### Adding a new CLI subcommand

1. Create `agent_replay/cli/cmd_<name>.py` with a Typer `app` object
2. Register it in `agent_replay/cli/main.py` via `app.add_typer(...)`
3. Add a `--json` flag if the command returns structured data
4. Write at least one CLI integration test using `typer.testing.CliRunner`

### Updating the pricing manifest

1. Edit `pricing/models.yaml`
2. Bump the `version` field (format: `YYYY-MM`)
3. Run `pytest tests/unit/test_cost.py` to verify no regressions
4. Update `docs/pricing.md` with the change summary

### Schema migration

1. Add a new migration string to the `MIGRATIONS` list in `store.py`
2. Bump `SCHEMA_VERSION` constant
3. The migration runs automatically on next DB connection
4. Write a migration test that opens an old-schema DB and verifies upgrade

---

## What Not To Do

- **Don't add a web server or REST API** — out of scope for v1. If users want
  a UI, `agent-replay export --format html` produces a self-contained report.
- **Don't use async in the Python SDK core** — the store and recorder are
  synchronous. Async wrappers can live in `integrations/` for async
  frameworks, but the persistence layer stays sync to keep it simple.
- **Don't add authentication or encryption** — the DB is a local file. If
  users need encrypted storage, they can put it on an encrypted volume. Not
  our problem to solve.
- **Don't normalize model names** — store them exactly as the provider
  returns them. Normalisation belongs in the pricing lookup with a fallback.
- **Don't import heavy dependencies in the core** — `rich` is allowed for CLI
  only (guarded by a `TYPE_CHECKING` or lazy import). The core
  (`recorder.py`, `store.py`, `session.py`) must import only stdlib.
- **Don't silently overwrite existing sessions** — if a session ID collision
  occurs (astronomically unlikely with UUID4 but still), raise a clear error.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AGENT_REPLAY_DB` | `~/.agent-replay/replay.db` | Path to SQLite database |
| `AGENT_REPLAY_PRICING` | `(bundled pricing/models.yaml)` | Path to custom pricing manifest |
| `AGENT_REPLAY_DISABLED` | unset | Set to `1` to disable all recording (no-op mode) |
| `AGENT_REPLAY_LOG_LEVEL` | `WARNING` | Python logging level for internal logs |

---

## Dependencies

### Python (`pyproject.toml`)
```toml
[project]
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",         # CLI
    "rich>=13",            # CLI output formatting
    "pyyaml>=6",           # pricing manifest
]

[project.optional-dependencies]
anthropic = ["anthropic>=0.30"]
openai    = ["openai>=1.30"]
langchain = ["langchain-core>=0.2"]
dev       = ["pytest", "mypy", "ruff", "pytest-cov"]
```

### TypeScript (`package.json`)
```json
{
  "dependencies": {
    "better-sqlite3": "^9.0"
  },
  "devDependencies": {
    "typescript": "^5.4",
    "@types/better-sqlite3": "^7",
    "vitest": "^1"
  }
}
```

---

## Git Conventions

- Branch names: `feat/<short-slug>`, `fix/<short-slug>`, `chore/<short-slug>`
- Commit messages: conventional commits — `feat:`, `fix:`, `docs:`, `test:`,
  `chore:`
- Every feature branch must include tests before merge
- `main` is always releasable — no broken tests, no `mypy` errors

---

## Release Checklist

Before tagging a release:

- [ ] `pytest` passes with zero failures
- [ ] `mypy --strict` passes with zero errors
- [ ] `ruff check` passes with zero warnings
- [ ] `pricing/models.yaml` version is current
- [ ] `CHANGELOG.md` updated
- [ ] `README.md` quickstart tested end-to-end from a fresh virtualenv
- [ ] TypeScript `npm run build` succeeds
- [ ] PyPI publish via `python -m build && twine upload dist/*`
- [ ] npm publish via `npm publish`
