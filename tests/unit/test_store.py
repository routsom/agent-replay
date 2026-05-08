"""Unit tests for store.py — SQLite persistence layer."""

from __future__ import annotations

from datetime import datetime

import pytest

from agent_replay.session import Session, Step
from agent_replay.store import Store


@pytest.fixture
def store() -> Store:
    """Create an in-memory store for testing."""
    s = Store(db_path=":memory:")
    # Force initialization
    s._get_conn()
    return s


@pytest.fixture
def sample_session() -> Session:
    """Create a sample session for testing."""
    return Session(
        id="test-session-001",
        name="test-session",
        framework="anthropic",
        model="claude-sonnet-4-6",
        started_at=datetime(2026, 5, 1, 10, 0, 0),
        status="completed",
        tags=["test", "unit"],
        metadata={"env": "ci"},
        total_input_tokens=100,
        total_output_tokens=200,
        total_cost_usd=0.005,
    )


@pytest.fixture
def sample_step() -> Step:
    """Create a sample step for testing."""
    return Step(
        id="test-step-001",
        session_id="test-session-001",
        sequence=0,
        type="llm_call",
        started_at=datetime(2026, 5, 1, 10, 0, 0),
        ended_at=datetime(2026, 5, 1, 10, 0, 2),
        latency_ms=2000,
        input={"prompt": "Hello"},
        output={"text": "Hi there!"},
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.001,
    )


class TestStore:
    def test_save_and_get_session(self, store: Store, sample_session: Session) -> None:
        store.save_session(sample_session)
        retrieved = store.get_session("test-session-001", include_steps=False)

        assert retrieved is not None
        assert retrieved.id == "test-session-001"
        assert retrieved.name == "test-session"
        assert retrieved.framework == "anthropic"
        assert retrieved.model == "claude-sonnet-4-6"
        assert retrieved.status == "completed"
        assert retrieved.tags == ["test", "unit"]
        assert retrieved.metadata == {"env": "ci"}
        assert retrieved.total_input_tokens == 100
        assert retrieved.total_output_tokens == 200
        assert retrieved.total_cost_usd == 0.005

    def test_get_nonexistent_session(self, store: Store) -> None:
        result = store.get_session("nonexistent", include_steps=False)
        assert result is None

    def test_save_and_get_step(
        self, store: Store, sample_session: Session, sample_step: Step
    ) -> None:
        store.save_session(sample_session)
        store.save_step(sample_step)

        steps = store.get_steps("test-session-001")
        assert len(steps) == 1
        assert steps[0].id == "test-step-001"
        assert steps[0].type == "llm_call"
        assert steps[0].input == {"prompt": "Hello"}
        assert steps[0].output == {"text": "Hi there!"}
        assert steps[0].input_tokens == 10
        assert steps[0].output_tokens == 20

    def test_list_sessions(self, store: Store) -> None:
        for i in range(5):
            s = Session(
                id=f"session-{i}",
                framework="anthropic",
                model="claude-sonnet-4-6",
                started_at=datetime(2026, 5, 1, 10, i, 0),
            )
            store.save_session(s)

        sessions = store.list_sessions(limit=3)
        assert len(sessions) == 3
        # Most recent first
        assert sessions[0].id == "session-4"

    def test_list_sessions_filter_framework(self, store: Store) -> None:
        store.save_session(Session(id="s1", framework="anthropic", model="claude"))
        store.save_session(Session(id="s2", framework="openai", model="gpt-4o"))
        store.save_session(Session(id="s3", framework="anthropic", model="claude"))

        sessions = store.list_sessions(framework="anthropic")
        assert len(sessions) == 2
        assert all(s.framework == "anthropic" for s in sessions)

    def test_list_sessions_filter_tag(self, store: Store) -> None:
        store.save_session(Session(id="s1", framework="x", model="m", tags=["prod", "v2"]))
        store.save_session(Session(id="s2", framework="x", model="m", tags=["dev"]))

        sessions = store.list_sessions(tag="prod")
        assert len(sessions) == 1
        assert sessions[0].id == "s1"

    def test_update_annotation_step(
        self, store: Store, sample_session: Session, sample_step: Step
    ) -> None:
        store.save_session(sample_session)
        store.save_step(sample_step)

        store.update_annotation(
            session_id="test-session-001",
            step_id="test-step-001",
            note="Great response",
            verdict="pass",
        )

        steps = store.get_steps("test-session-001")
        assert steps[0].annotation == "Great response"
        assert steps[0].verdict == "pass"

    def test_update_annotation_session(
        self, store: Store, sample_session: Session
    ) -> None:
        store.save_session(sample_session)

        store.update_annotation(
            session_id="test-session-001",
            note="Overall good run",
            verdict="pass",
        )

        session = store.get_session("test-session-001", include_steps=False)
        assert session is not None
        assert session.metadata.get("annotation") == "Overall good run"
        assert session.metadata.get("verdict") == "pass"

    def test_delete_session(
        self, store: Store, sample_session: Session, sample_step: Step
    ) -> None:
        store.save_session(sample_session)
        store.save_step(sample_step)

        store.delete_session("test-session-001")

        assert store.get_session("test-session-001") is None
        assert store.get_steps("test-session-001") == []

    def test_session_with_steps(
        self, store: Store, sample_session: Session, sample_step: Step
    ) -> None:
        store.save_session(sample_session)
        store.save_step(sample_step)

        session = store.get_session("test-session-001", include_steps=True)
        assert session is not None
        assert len(session.steps) == 1
        assert session.steps[0].id == "test-step-001"

    def test_multiple_steps_ordered(
        self, store: Store, sample_session: Session
    ) -> None:
        store.save_session(sample_session)
        for i in range(5):
            step = Step(
                id=f"step-{i}",
                session_id="test-session-001",
                sequence=i,
                type="llm_call",
                started_at=datetime(2026, 5, 1, 10, 0, i),
            )
            store.save_step(step)

        steps = store.get_steps("test-session-001")
        assert len(steps) == 5
        assert [s.sequence for s in steps] == [0, 1, 2, 3, 4]

    def test_session_update(self, store: Store, sample_session: Session) -> None:
        store.save_session(sample_session)
        sample_session.status = "error"
        sample_session.ended_at = datetime(2026, 5, 1, 10, 5, 0)
        store.save_session(sample_session)

        session = store.get_session("test-session-001", include_steps=False)
        assert session is not None
        assert session.status == "error"
        assert session.ended_at is not None
