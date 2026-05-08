# Quickstart

Get full agent tracing in under 60 seconds. No server, no cloud account — just one SQLite file.

## Install

```bash
pip install agent-replay
```

## Option 1: Decorator (simplest)

```python
from agent_replay import record

@record(name="my-agent-run", tags=["prod", "v2"])
def run_my_agent(prompt: str) -> str:
    # your agent code here
    return "result"

run_my_agent("Hello, agent!")
```

## Option 2: Context Manager

```python
from agent_replay import Recorder

with Recorder(name="my-run", framework="anthropic", model="claude-sonnet-4-6") as r:
    step = r.step("llm_call", input={"prompt": "Hello!"})
    # ... call your LLM ...
    step.finish(
        output={"text": "Hi there!"},
        input_tokens=25,
        output_tokens=40,
    )
```

## Option 3: Drop-in Anthropic Wrapper

```python
from anthropic import Anthropic
from agent_replay.integrations.anthropic import ReplayClient

client = ReplayClient(Anthropic(), session_name="customer-support")
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}],
)
client.end()
```

## View Your Traces

```bash
# List recent sessions
agent-replay list

# Show details for a session
agent-replay show <session-id> --steps

# Export as HTML report
agent-replay export <session-id> --format html --out report.html
```

## What Gets Recorded

Every step captures:
- **Input/Output**: Raw request and response data
- **Token usage**: Input and output token counts
- **Cost**: Calculated from the bundled pricing manifest
- **Latency**: Time taken for each step
- **Errors**: Any exceptions that occurred

All stored in a single SQLite file at `~/.agent-replay/replay.db`.
Override with `AGENT_REPLAY_DB` environment variable.

## Next Steps

- [Integrations](integrations.md) — LangChain, OpenAI, Google ADK, CrewAI
- [Schema Reference](schema.md) — Database schema details
- [Pricing](pricing.md) — Token cost configuration
