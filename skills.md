# Skills & Techniques Used in This Project

A record of the engineering decisions and techniques applied to bring
**agent-replay** to open-source release quality.

---

## 1. Python Type Safety — `mypy --strict`

Resolved 21 strict-mode type errors across 5 files with zero logic changes:

| File | Problem | Fix |
|---|---|---|
| `pricing.py` | Return type had 4 nesting levels instead of 3 | Corrected to `dict[str, dict[str, dict[str, float]]]` |
| `store.py` | `tuple[object, ...]` row type blocked `int()`/`float()` casts | Changed private row helpers to `Any` (sqlite3 rows are untyped at runtime) |
| `recorder.py` | `Store | None` union caused attr errors after disabled-mode guard | Narrowed via `if self._disabled or self._store is None:` and local variable assignment |
| `langchain.py` | `_active_steps` typed as `dict[str, StepContext]` but `Recorder.step()` returns a union | Updated to `dict[str, StepContext | _NoOpStepContext]` |
| `pricing.py` | `yaml` module lacked type stubs | Installed `types-PyYAML` |

**Principle:** never use `# type: ignore` as a first resort — fix the underlying type model.

---

## 2. SQLite Persistence Pattern

- Raw `sqlite3` with parameterised queries — no ORM
- `PRAGMA journal_mode=WAL` for concurrent read safety
- `PRAGMA foreign_keys=ON` to enforce `ON DELETE CASCADE` on steps
- `INSERT … ON CONFLICT DO UPDATE` (upsert) for sessions to avoid cascading deletes on re-save
- Schema version tracked via `PRAGMA user_version`; migrations applied as an ordered list of SQL strings

---

## 3. Fail-Silent Tracing

Every store operation is wrapped so tracing can never break user code:

```python
store = self._recorder._store
if store is not None:
    try:
        store.save_step(self.step)
    except Exception as e:
        logger.warning("agent-replay: failed to save step: %s", e)
```

---

## 4. Zero-Overhead Disabled Mode

`AGENT_REPLAY_DISABLED=1` makes every decorator and context manager a true
no-op — no DB connection opened, no objects allocated:

```python
if self._disabled or self._store is None:
    return self
```

Checked both at import time (decorator) and at call time (wrapper function).

---

## 5. Testing Strategy

- **63 tests, 0 failures** across unit and integration suites
- Integration tests use real in-memory SQLite (`:memory:`) — no mock stores
- Only external LLM API calls are mocked (`unittest.mock.MagicMock`)
- Golden fixture at `tests/fixtures/sample_session.json` is the source of truth for diff/replay output

---

## 6. CLI Design

- Built with [Typer](https://typer.tiangolo.com/) for automatic `--help` generation
- Every command with structured output has a `--json` flag for machine-readable piping
- Human-first default output via [Rich](https://rich.readthedocs.io/) tables and panels
- All subcommands accept `--db` to override the database path

---

## 7. Multi-Framework Integration Pattern

Each integration follows the same shape:

1. Intercept the provider's API call
2. Call `recorder.step(type, input=...)` before the call
3. Call `step.finish(output=..., input_tokens=..., output_tokens=...)` after
4. Re-raise any exception so user code is never swallowed

Implemented for: Anthropic, OpenAI, LangChain, Google ADK, CrewAI.

---

## 8. Cost Calculation

- Single YAML manifest (`pricing/models.yaml`) as source of truth
- Loaded once and cached in-process; `reset_pricing_cache()` exposed for tests
- Returns `0.0` with a warning for unknown models — never raises
- Version field in manifest (`YYYY-MM`) tracks when prices were last updated

---

## 9. Open-Source Readiness Checklist

| Item | Status |
|---|---|
| `LICENSE` (MIT) | Added |
| `.gitignore` | Added |
| `CHANGELOG.md` | Added |
| `CONTRIBUTING.md` | Added |
| `pyproject.toml` URLs | Updated to `github.com/routsom/agent-replay` |
| `pytest` 0 failures | 63/63 passing |
| `mypy --strict` 0 errors | Clean across 24 source files |
| `ruff check` 0 warnings | Clean |

---

## 10. TypeScript SDK

Mirrors the Python API with `better-sqlite3` (synchronous — no async in the core):

```typescript
const recorder = new Recorder({ name: 'my-run', framework: 'anthropic' })
const session = await recorder.start()
const step = session.step('llm_call', { prompt })
// ... call LLM ...
await step.finish({ output, inputTokens, outputTokens })
await session.end()
```

Integrations for Anthropic and OpenAI follow the same intercept-and-record pattern as the Python SDK.
