"""Core Recorder class for agent-replay.

Provides context manager and decorator patterns for recording agent sessions.
All store operations are wrapped in try/except — tracing never breaks user code.

When ``AGENT_REPLAY_DISABLED=1`` the decorator and context manager become true
no-ops with zero overhead — no Store is opened, no objects are allocated.
"""

from __future__ import annotations

import functools
import logging
import os
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from agent_replay.cost import calculate_cost
from agent_replay.session import Session, Step
from agent_replay.store import Store

logger = logging.getLogger("agent_replay")


def _is_disabled() -> bool:
    """Check if recording is disabled via environment variable."""
    return os.environ.get("AGENT_REPLAY_DISABLED", "").strip() == "1"


class _NoOpStepContext:
    """A step context that does nothing — used when recording is disabled."""

    def __init__(self) -> None:
        self.step = Step()

    def finish(
        self,
        output: dict[str, object] | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        error: str | None = None,
    ) -> Step:
        return self.step


class StepContext:
    """Context for recording a single step within a session."""

    def __init__(
        self,
        recorder: Recorder,
        step_type: str,
        input: dict[str, object] | None = None,  # noqa: A002
    ) -> None:
        self._recorder = recorder
        self.step = Step(
            id=str(uuid.uuid4()),
            session_id=recorder.session.id,
            sequence=recorder._next_sequence(),
            type=step_type,
            started_at=datetime.now(),
            input=input or {},
        )

    def finish(
        self,
        output: dict[str, object] | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        error: str | None = None,
    ) -> Step:
        """Complete the step with output data and token counts."""
        self.step.ended_at = datetime.now()
        self.step.output = output or {}
        self.step.input_tokens = input_tokens
        self.step.output_tokens = output_tokens
        self.step.error = error

        # Calculate latency
        if self.step.ended_at and self.step.started_at:
            delta = self.step.ended_at - self.step.started_at
            self.step.latency_ms = int(delta.total_seconds() * 1000)

        # Calculate cost
        self.step.cost_usd = calculate_cost(
            model=self._recorder.session.model,
            provider=self._recorder.session.framework,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Update session totals
        self._recorder.session.total_input_tokens += input_tokens
        self._recorder.session.total_output_tokens += output_tokens
        self._recorder.session.total_cost_usd += self.step.cost_usd

        # Persist step
        store = self._recorder._store
        if store is not None:
            try:
                store.save_step(self.step)
            except Exception as e:
                logger.warning("agent-replay: failed to save step: %s", e)

        return self.step


class Recorder:
    """Records an agent session to SQLite.

    When ``AGENT_REPLAY_DISABLED=1`` is set, the Recorder becomes a true
    no-op — no database connection is opened and no objects are allocated
    beyond the Recorder itself. Safe for production with zero overhead.

    Usage as context manager::

        with Recorder(name="my-run", framework="anthropic") as r:
            step = r.step("llm_call", input={"prompt": prompt})
            response = client.messages.create(...)
            step.finish(output={"text": response.content[0].text},
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens)

    Usage as decorator::

        @record(name="my-agent-run", tags=["prod", "v2"])
        def run_my_agent(prompt: str) -> str:
            ...
    """

    def __init__(
        self,
        name: str | None = None,
        framework: str = "custom",
        model: str = "unknown",
        tags: list[str] | None = None,
        metadata: dict[str, object] | None = None,
        db_path: str | None = None,
    ) -> None:
        self._disabled = _is_disabled()
        self._sequence_counter = 0

        if self._disabled:
            # No-op mode: don't open DB or allocate heavy objects
            self._store: Store | None = None
            self.session = Session(name=name)
            return

        self._store = Store(db_path=db_path)
        self.session = Session(
            id=str(uuid.uuid4()),
            name=name,
            framework=framework,
            model=model,
            started_at=datetime.now(),
            tags=tags or [],
            metadata=metadata or {},
        )

    def _next_sequence(self) -> int:
        """Return and increment the step sequence counter."""
        seq = self._sequence_counter
        self._sequence_counter += 1
        return seq

    def step(
        self,
        step_type: str,
        input: dict[str, object] | None = None,  # noqa: A002
    ) -> StepContext | _NoOpStepContext:
        """Create a new step context for recording."""
        if self._disabled:
            return _NoOpStepContext()
        return StepContext(self, step_type, input)

    def __enter__(self) -> Recorder:
        if self._disabled or self._store is None:
            return self
        try:
            self._store.save_session(self.session)
        except Exception as e:
            logger.warning("agent-replay: failed to save session: %s", e)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        store = self._store
        if self._disabled or store is None:
            return
        self.session.ended_at = datetime.now()
        self.session.status = "error" if exc_type else "completed"
        try:
            store.save_session(self.session)
        except Exception as e:
            logger.warning("agent-replay: failed to finalize session: %s", e)
        finally:
            store.close()

    def end(self, status: str = "completed") -> None:
        """Manually end the session (for non-context-manager usage)."""
        store = self._store
        if self._disabled or store is None:
            return
        self.session.ended_at = datetime.now()
        self.session.status = status
        try:
            store.save_session(self.session)
        except Exception as e:
            logger.warning("agent-replay: failed to finalize session: %s", e)


def record(
    name: str | None = None,
    framework: str = "custom",
    model: str = "unknown",
    tags: list[str] | None = None,
    metadata: dict[str, object] | None = None,
    db_path: str | None = None,
) -> Callable[..., Any]:
    """Decorator that wraps a function with session recording.

    When ``AGENT_REPLAY_DISABLED=1``, becomes a pure passthrough
    with zero overhead — the function runs exactly as if undecorated.

    Usage::

        @record(name="my-agent-run", tags=["prod", "v2"])
        def run_my_agent(prompt: str) -> str:
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # If disabled at import time, return the function untouched
        if _is_disabled():
            return func

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Also check at call time (env var may change)
            if _is_disabled():
                return func(*args, **kwargs)
            with Recorder(
                name=name or func.__name__,
                framework=framework,
                model=model,
                tags=tags,
                metadata=metadata,
                db_path=db_path,
            ):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def record_if(
    condition: bool | Callable[[], bool],
    **kwargs: Any,
) -> Callable[..., Any]:
    """Conditional decorator — only records when condition is True.

    Useful for environment-based gating in production::

        @record_if(os.environ.get("ENABLE_TRACING") == "1",
                   name="my-agent")
        def run_agent(prompt: str) -> str:
            ...

        # Or with a callable for dynamic evaluation:
        @record_if(lambda: settings.TRACING_ENABLED,
                   name="my-agent")
        def run_agent(prompt: str) -> str:
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kw: Any) -> Any:
            should_record = condition() if callable(condition) else condition
            if not should_record or _is_disabled():
                return func(*args, **kw)
            with Recorder(
                name=kwargs.get("name") or func.__name__,
                framework=kwargs.get("framework", "custom"),
                model=kwargs.get("model", "unknown"),
                tags=kwargs.get("tags"),
                metadata=kwargs.get("metadata"),
                db_path=kwargs.get("db_path"),
            ):
                return func(*args, **kw)

        return wrapper

    return decorator

