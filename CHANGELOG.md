# Changelog

All notable changes to agent-replay will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-05-08

### Added
- Core `Recorder` class with context manager and `@record` decorator patterns
- `record_if` conditional decorator for environment-based gating
- SQLite persistence layer (`Store`) with WAL mode and schema migrations
- `Session` and `Step` dataclasses as the canonical data model
- Token cost calculator with bundled `pricing/models.yaml` manifest
- Diff engine comparing two sessions by step sequence
- Replay engine re-executing sessions against a new model
- JSONL and self-contained HTML export
- `AGENT_REPLAY_DISABLED=1` kill-switch for zero-overhead no-op mode
- CLI: `list`, `show`, `diff`, `replay`, `annotate`, `export`, `stats`
- Anthropic SDK drop-in wrapper (`ReplayClient`)
- OpenAI SDK drop-in wrapper (`ReplayClient`)
- LangChain callback handler (`ReplayCallbackHandler`)
- Google ADK integration
- CrewAI integration
- TypeScript SDK with `better-sqlite3` and Anthropic/OpenAI integrations
- Pricing manifest for Anthropic, OpenAI, and Google models (version 2026-05)
- 63 unit and integration tests; `mypy --strict` and `ruff` clean
