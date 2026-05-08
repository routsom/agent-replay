"""Unit tests for diff.py — Diff engine."""

from __future__ import annotations

from datetime import datetime

import pytest

from agent_replay.diff import diff_sessions
from agent_replay.session import Session, Step
from agent_replay.store import Store


@pytest.fixture
def store() -> Store:
    return Store(db_path=":memory:")


def _make_session(store: Store, sid: str, steps: list[dict[str, object]]) -> None:
    session = Session(
        id=sid, framework="anthropic", model="claude",
        started_at=datetime(2026, 5, 1),
        total_input_tokens=sum(int(s.get("input_tokens", 0)) for s in steps),
        total_output_tokens=sum(int(s.get("output_tokens", 0)) for s in steps),
        total_cost_usd=sum(float(s.get("cost_usd", 0.0)) for s in steps),
    )
    store.save_session(session)
    for i, s in enumerate(steps):
        step = Step(
            id=f"{sid}-s-{i}", session_id=sid, sequence=i,
            type=str(s.get("type", "llm_call")),
            started_at=datetime(2026, 5, 1, 10, 0, i),
            input=dict(s.get("input", {})) if isinstance(s.get("input"), dict) else {},
            output=dict(s.get("output", {})) if isinstance(s.get("output"), dict) else {},
            input_tokens=int(s.get("input_tokens", 0)),
            output_tokens=int(s.get("output_tokens", 0)),
            cost_usd=float(s.get("cost_usd", 0.0)),
        )
        store.save_step(step)


class TestDiff:
    def test_identical(self, store: Store) -> None:
        steps = [{"type": "llm_call", "input": {"p": "hi"}, "output": {"t": "hello"}}]
        _make_session(store, "a", steps)
        _make_session(store, "b", steps)
        r = diff_sessions("a", "b", store=store)
        assert not r.steps_added and not r.steps_removed and not r.steps_changed

    def test_added(self, store: Store) -> None:
        _make_session(store, "a", [{"input": {"p": "1"}, "output": {"t": "1"}}])
        _make_session(store, "b", [
            {"input": {"p": "1"}, "output": {"t": "1"}},
            {"input": {"p": "2"}, "output": {"t": "2"}},
        ])
        r = diff_sessions("a", "b", store=store)
        assert len(r.steps_added) == 1

    def test_removed(self, store: Store) -> None:
        _make_session(store, "a", [
            {"input": {"p": "1"}, "output": {"t": "1"}},
            {"input": {"p": "2"}, "output": {"t": "2"}},
        ])
        _make_session(store, "b", [{"input": {"p": "1"}, "output": {"t": "1"}}])
        r = diff_sessions("a", "b", store=store)
        assert len(r.steps_removed) == 1

    def test_changed(self, store: Store) -> None:
        _make_session(store, "a", [{"input": {"p": "hi"}, "output": {"t": "1"}}])
        _make_session(store, "b", [{"input": {"p": "hi"}, "output": {"t": "2"}}])
        r = diff_sessions("a", "b", store=store)
        assert len(r.steps_changed) == 1

    def test_cost_delta(self, store: Store) -> None:
        _make_session(store, "a", [{"cost_usd": 0.01, "input_tokens": 100, "output_tokens": 100}])
        _make_session(store, "b", [{"cost_usd": 0.05, "input_tokens": 500, "output_tokens": 500}])
        r = diff_sessions("a", "b", store=store)
        assert r.cost_delta_usd == pytest.approx(0.04)
        assert r.token_delta == 800

    def test_missing_session(self, store: Store) -> None:
        _make_session(store, "a", [])
        with pytest.raises(ValueError):
            diff_sessions("a", "nope", store=store)
