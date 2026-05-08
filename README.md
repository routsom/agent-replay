# agent-replay

> Dead-simple, local-first, framework-agnostic agent observability.

**One decorator. One SQLite file. Full tracing. No server. No cloud account. Zero infrastructure.**

[![PyPI version](https://img.shields.io/pypi/v/agent-replay?color=blue)](https://pypi.org/project/agent-replay/)
[![Python](https://img.shields.io/pypi/pyversions/agent-replay)](https://pypi.org/project/agent-replay/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-63%20passed-brightgreen)](tests/)
[![mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/)
[![ruff](https://img.shields.io/badge/linter-ruff-orange)](https://docs.astral.sh/ruff/)

---

## What it looks like

**`agent-replay list`** — table of all recorded sessions:

```
                          Agent Sessions
 ┌──────────────┬──────────────────┬───────────┬───────────────────┬───────┬─────────┬──────────┬───────────┬──────────────────┐
 │ ID           │ Name             │ Framework │ Model             │ Steps │ Tokens  │ Cost     │ Status    │ Started          │
 ├──────────────┼──────────────────┼───────────┼───────────────────┼───────┼─────────┼──────────┼───────────┼──────────────────┤
 │ a3f2c1b9e8d7 │ customer-support │ anthropic │ claude-sonnet-4-6 │ 6     │ 4,821   │ $0.0867  │ completed │ 2026-05-08 14:02 │
 │ 9c8b7a6d5e4f │ research-agent   │ openai    │ gpt-4o            │ 12    │ 11,340  │ $0.1418  │ completed │ 2026-05-08 13:47 │
 │ 1e2d3c4b5a69 │ langchain-chain  │ langchain │ claude-haiku-4-5  │ 4     │ 2,105   │ $0.0042  │ error     │ 2026-05-08 13:31 │
 └──────────────┴──────────────────┴───────────┴───────────────────┴───────┴─────────┴──────────┴───────────┴──────────────────┘
```

**`agent-replay show <id> --steps`** — full session breakdown:

```
 ╭──────────────────────────────────── Session ─────────────────────────────────────╮
 │ ID:         a3f2c1b9e8d7d4e5f6a7b8c9                                             │
 │ Name:       customer-support                                                      │
 │ Framework:  anthropic                                                             │
 │ Model:      claude-sonnet-4-6                                                     │
 │ Status:     completed                                                             │
 │ Started:    2026-05-08 14:02:11                                                   │
 │ Ended:      2026-05-08 14:02:19                                                   │
 │ Steps:      6                                                                     │
 │ Tokens:     4,821 (3,204 in / 1,617 out)                                          │
 │ Cost:       $0.0867                                                               │
 ╰───────────────────────────────────────────────────────────────────────────────────╯

  Steps
 ┌───┬─────────────┬─────────┬───────────────┬──────────┬───────┬─────────┐
 │ # │ Type        │ Latency │ Tokens        │ Cost     │ Error │ Verdict │
 ├───┼─────────────┼─────────┼───────────────┼──────────┼───────┼─────────┤
 │ 0 │ llm_call    │ 1842ms  │ 512 / 280     │ $0.0154  │ —     │ pass    │
 │ 1 │ tool_call   │  124ms  │ 0 / 0         │ $0.0000  │ —     │ —       │
 │ 2 │ tool_result │   18ms  │ 0 / 0         │ $0.0000  │ —     │ —       │
 │ 3 │ llm_call    │ 2103ms  │ 890 / 441     │ $0.0329  │ —     │ pass    │
 └───┴─────────────┴─────────┴───────────────┴──────────┴───────┴─────────┘
```

**`agent-replay diff <id-a> <id-b>`** — spot what changed between two runs:

```
 ╭──────────── Diff: a3f2c1b9 ↔ 9c8b7a6d ────────────╮
 │ Steps: 2 changed. Cost delta: +$0.0551.            │
 ╰─────────────────────────────────────────────────────╯
   Token delta:  +6,519
   Cost delta:   +$0.0551

  Changed Steps (2)
 ┌───┬──────────┬──────────┬──────────┬──────────┐
 │ # │ Type A   │ Type B   │ Tokens A │ Tokens B │
 ├───┼──────────┼──────────┼──────────┼──────────┤
 │ 0 │ llm_call │ llm_call │ 792      │ 4,210    │
 │ 3 │ llm_call │ llm_call │ 1,331    │ 5,450    │
 └───┴──────────┴──────────┴──────────┴──────────┘
```

**`agent-replay stats --days 7`** — weekly cost & token report:

```
 ╭──────────────────────── Usage Statistics ─────────────────────────╮
 │ Period:        Last 7 days                                         │
 │ Sessions:      47                                                  │
 │ Steps:         312                                                 │
 │ Input tokens:  284,502                                             │
 │ Output tokens: 97,841                                              │
 │ Total tokens:  382,343                                             │
 │ Total cost:    $4.2917                                             │
 ╰────────────────────────────────────────────────────────────────────╯

  By Framework
 ┌───────────┬──────────┬─────────┬──────────┐
 │ Framework │ Sessions │ Tokens  │ Cost     │
 ├───────────┼──────────┼─────────┼──────────┤
 │ anthropic │ 31       │ 241,880 │ $3.1042  │
 │ openai    │ 12       │ 118,304 │ $0.9871  │
 │ langchain │ 4        │ 22,159  │ $0.2004  │
 └───────────┴──────────┴─────────┴──────────┘
```

---

## Install

```bash
pip install agent-replay
```

With a specific provider:

```bash
pip install "agent-replay[anthropic]"
pip install "agent-replay[openai]"
pip install "agent-replay[langchain]"
```

---

## Quick Start

### Decorator — simplest possible

```python
from agent_replay import record

@record(name="my-agent-run", tags=["prod", "v2"])
def run_my_agent(prompt: str) -> str:
    # your agent code here — nothing else changes
    return "result"
```

### Drop-in Anthropic wrapper

```python
from anthropic import Anthropic
from agent_replay.integrations.anthropic import ReplayClient

client = ReplayClient(Anthropic(), session_name="customer-support")
response = client.messages.create(model="claude-sonnet-4-6", ...)
client.end()
# every call is automatically traced — no other changes needed
```

### Context manager — full control

```python
from agent_replay import Recorder

with Recorder(name="my-run", framework="anthropic") as r:
    step = r.step("llm_call", input={"prompt": prompt})
    response = client.messages.create(...)
    step.finish(
        output={"text": response.content[0].text},
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
```

---

## CLI Reference

```
agent-replay list                              # table of recent sessions
agent-replay list --tag prod --framework anthropic
agent-replay show <id> --steps                # full detail + per-step breakdown
agent-replay show <id> --json                 # machine-readable output
agent-replay diff <id-a> <id-b>               # side-by-side comparison
agent-replay replay <id> --model gpt-4o       # re-run against a different model
agent-replay replay <id> --dry-run            # preview without executing
agent-replay annotate <id> --note "Looks good" --verdict pass
agent-replay export <id> --format html --out report.html
agent-replay export <id> --format jsonl       # one JSON line per step
agent-replay stats --days 7                   # aggregate cost + token usage
```

All commands accept `--db <path>` to point at a different database file.

---

## What Gets Recorded

Every step captures:

| Field | Description |
|---|---|
| `type` | `llm_call` / `tool_call` / `tool_result` / `reasoning` / `message` |
| `input` | Raw input dict — prompt, tool args, messages list |
| `output` | Raw output dict — response text, tool result |
| `input_tokens` | Tokens sent to the model |
| `output_tokens` | Tokens generated by the model |
| `cost_usd` | Auto-calculated from the bundled pricing manifest |
| `latency_ms` | Wall-clock time for this step |
| `error` | Exception message if the step failed |
| `annotation` | Human note attached via `agent-replay annotate` |
| `verdict` | `pass` / `fail` for building eval datasets |

Everything lives in a single SQLite file at `~/.agent-replay/replay.db`.
Override with `AGENT_REPLAY_DB=/path/to/custom.db`.

---

## Integrations

| Framework | Install | Usage |
|---|---|---|
| **Anthropic** | `pip install "agent-replay[anthropic]"` | `ReplayClient(Anthropic(), ...)` |
| **OpenAI** | `pip install "agent-replay[openai]"` | `ReplayClient(OpenAI(), ...)` |
| **LangChain** | `pip install "agent-replay[langchain]"` | `ReplayCallbackHandler(...)` |
| **Google ADK** | included | `ReplayEventHandler(...)` |
| **CrewAI** | included | `ReplayObserver(...)` |
| **TypeScript** | `npm install agent-replay` | `new Recorder({ ... })` |

---

## Production Safety

agent-replay **never breaks your agent**. Every store operation is wrapped in
`try/except` — tracing is always best-effort, never load-bearing.

### Kill switch — zero overhead

```bash
export AGENT_REPLAY_DISABLED=1
```

No database is opened, no objects are allocated. Every decorator and context
manager becomes a pure passthrough with zero overhead.

### Conditional decorator

```python
import os
from agent_replay import record_if

@record_if(os.environ.get("ENABLE_TRACING") == "1", name="my-agent")
def run_agent(prompt: str) -> str:
    ...
```

### Dev-only dependency

```toml
# pyproject.toml — only install in dev/staging
[project.optional-dependencies]
dev = ["agent-replay"]
```

```python
try:
    from agent_replay import record
except ImportError:
    def record(**kw):   # no-op fallback
        return lambda f: f
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `AGENT_REPLAY_DB` | `~/.agent-replay/replay.db` | SQLite database path |
| `AGENT_REPLAY_PRICING` | bundled | Path to custom pricing manifest |
| `AGENT_REPLAY_DISABLED` | unset | Set to `1` to disable all recording |
| `AGENT_REPLAY_LOG_LEVEL` | `WARNING` | Internal log level |

---

## Development

```bash
git clone https://github.com/routsom/agent-replay
cd agent-replay
pip install -e ".[dev]"

pytest tests/ -v           # 63 tests, 0 failures
mypy agent_replay/ --strict  # 0 errors
ruff check agent_replay/     # 0 warnings
```

---

## License

[MIT](LICENSE) — Copyright (c) 2026 agent-replay contributors
