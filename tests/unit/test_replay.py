"""Unit tests for replay.py — Replay engine."""

from __future__ import annotations

from datetime import datetime

import pytest

from agent_replay.replay import replay_session
from agent_replay.session import Session, Step
from agent_replay.store import Store


@pytest.fixture
def store() -> Store:
    s = Store(db_path=":memory:")
    # Seed a session with steps
    session = Session(
        id="orig-001", name="original", framework="anthropic",
        model="claude-sonnet-4-6", started_at=datetime(2026, 5, 1),
        ended_at=datetime(2026, 5, 1, 0, 1), status="completed",
        tags=["test"], total_input_tokens=100, total_output_tokens=200,
        total_cost_usd=0.005,
    )
    s.save_session(session)
    for i in range(3):
        step = Step(
            id=f"orig-step-{i}", session_id="orig-001", sequence=i,
            type="llm_call", started_at=datetime(2026, 5, 1, 0, 0, i),
            input={"prompt": f"prompt-{i}"}, output={"text": f"response-{i}"},
            input_tokens=30 + i * 10, output_tokens=60 + i * 10,
        )
        s.save_step(step)
    return s


class TestReplay:
    def test_replay_creates_new_session(self, store: Store) -> None:
        result = replay_session("orig-001", store=store)
        assert result is not None
        assert result.id != "orig-001"
        assert result.status == "completed"
        assert "replay" in result.tags
        assert result.metadata.get("replayed_from") == "orig-001"

    def test_replay_copies_steps(self, store: Store) -> None:
        result = replay_session("orig-001", store=store)
        assert result is not None
        assert len(result.steps) == 3

    def test_replay_model_override(self, store: Store) -> None:
        result = replay_session("orig-001", model_override="gpt-4o", store=store)
        assert result is not None
        assert result.model == "gpt-4o"
        assert result.metadata.get("original_model") == "claude-sonnet-4-6"

    def test_replay_dry_run(self, store: Store, capsys: pytest.CaptureFixture[str]) -> None:
        result = replay_session("orig-001", dry_run=True, store=store)
        assert result is None
        captured = capsys.readouterr()
        assert "Replay Plan" in captured.out

    def test_replay_missing_session(self, store: Store) -> None:
        with pytest.raises(ValueError, match="Session not found"):
            replay_session("nonexistent", store=store)

    def test_replay_persisted(self, store: Store) -> None:
        result = replay_session("orig-001", store=store)
        assert result is not None
        persisted = store.get_session(result.id, include_steps=True)
        assert persisted is not None
        assert len(persisted.steps) == 3
