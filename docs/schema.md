# SQLite Schema Reference

agent-replay stores all data in a single SQLite file. Default location: `~/.agent-replay/replay.db`.

## Tables

### sessions

| Column | Type | Description |
|---|---|---|
| `id` | TEXT PK | UUID4 session identifier |
| `name` | TEXT | Optional human label |
| `framework` | TEXT NOT NULL | Framework identifier (anthropic, openai, etc.) |
| `model` | TEXT NOT NULL | Model name as returned by provider |
| `started_at` | TEXT NOT NULL | ISO-8601 timestamp |
| `ended_at` | TEXT | ISO-8601 timestamp |
| `status` | TEXT NOT NULL | running, completed, or error |
| `tags` | TEXT | JSON array of strings |
| `metadata` | TEXT | JSON object for arbitrary key-value data |
| `total_input_tokens` | INTEGER | Sum of all step input tokens |
| `total_output_tokens` | INTEGER | Sum of all step output tokens |
| `total_cost_usd` | REAL | Sum of all step costs |

### steps

| Column | Type | Description |
|---|---|---|
| `id` | TEXT PK | UUID4 step identifier |
| `session_id` | TEXT FK | References sessions(id), cascading delete |
| `sequence` | INTEGER | 0-indexed order within session |
| `type` | TEXT NOT NULL | llm_call, tool_call, tool_result, reasoning, message |
| `started_at` | TEXT NOT NULL | ISO-8601 timestamp |
| `ended_at` | TEXT | ISO-8601 timestamp |
| `latency_ms` | INTEGER | Duration in milliseconds |
| `input` | TEXT | JSON — raw input data |
| `output` | TEXT | JSON — raw output data |
| `input_tokens` | INTEGER | Input token count |
| `output_tokens` | INTEGER | Output token count |
| `cost_usd` | REAL | Cost for this step |
| `error` | TEXT | Exception message if step failed |
| `annotation` | TEXT | Human note (via annotate command) |
| `verdict` | TEXT | pass or fail |

## Indexes

- `idx_steps_session` — (session_id, sequence) for fast step retrieval
- `idx_sessions_framework` — (framework) for filtering
- `idx_sessions_started` — (started_at) for time-based queries

## Migrations

Schema migrations are stored as a versioned list in `store.py`. On each connection, the current `PRAGMA user_version` is checked and any pending migrations are applied automatically.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `AGENT_REPLAY_DB` | `~/.agent-replay/replay.db` | Custom database path |
