"""Unit tests for recorder.py — Core Recorder class."""

from __future__ import annotations

import os
from datetime import datetime
from unittest.mock import patch

import pytest

from agent_replay.recorder import Recorder, record
from agent_replay.store import Store


@pytest.fixture
def store() -> Store:
    return Store(db_path=":memory:")


class TestRecorder:
    def test_context_manager_basic(self) -> None:
        with Recorder(name="test", framework="anthropic", model="test-model", db_path=":memory:") as r:
            assert r.session.name == "test"
            assert r.session.framework == "anthropic"
            assert r.session.status == "running"

        assert r.session.status == "completed"
        assert r.session.ended_at is not None

    def test_step_recording(self) -> None:
        with Recorder(name="test", db_path=":memory:") as r:
            step = r.step("llm_call", input={"prompt": "hello"})
            result = step.finish(
                output={"text": "hi"},
                input_tokens=10,
                output_tokens=20,
            )

            assert result.type == "llm_call"
            assert result.input == {"prompt": "hello"}
            assert result.output == {"text": "hi"}
            assert result.input_tokens == 10
            assert result.output_tokens == 20
            assert result.latency_ms is not None

    def test_session_totals_accumulate(self) -> None:
        with Recorder(name="test", db_path=":memory:") as r:
            step1 = r.step("llm_call")
            step1.finish(input_tokens=100, output_tokens=200)

            step2 = r.step("llm_call")
            step2.finish(input_tokens=50, output_tokens=100)

        assert r.session.total_input_tokens == 150
        assert r.session.total_output_tokens == 300

    def test_sequence_increments(self) -> None:
        with Recorder(name="test", db_path=":memory:") as r:
            s0 = r.step("llm_call")
            s0.finish()
            s1 = r.step("tool_call")
            s1.finish()
            s2 = r.step("llm_call")
            s2.finish()

        assert s0.step.sequence == 0
        assert s1.step.sequence == 1
        assert s2.step.sequence == 2

    def test_error_status_on_exception(self) -> None:
        try:
            with Recorder(name="test", db_path=":memory:") as r:
                raise ValueError("test error")
        except ValueError:
            pass

        assert r.session.status == "error"

    def test_step_error_recording(self) -> None:
        with Recorder(name="test", db_path=":memory:") as r:
            step = r.step("llm_call")
            result = step.finish(error="API timeout")

        assert result.error == "API timeout"

    def test_disabled_mode(self) -> None:
        with patch.dict(os.environ, {"AGENT_REPLAY_DISABLED": "1"}):
            with Recorder(name="test", db_path=":memory:") as r:
                step = r.step("llm_call")
                step.finish()

            # Should still work, just not persist
            assert r.session is not None

    def test_manual_end(self) -> None:
        r = Recorder(name="test", db_path=":memory:")
        r.__enter__()
        step = r.step("llm_call")
        step.finish(input_tokens=10, output_tokens=20)
        r.end(status="completed")

        assert r.session.status == "completed"
        assert r.session.ended_at is not None


class TestRecordDecorator:
    def test_decorator_basic(self) -> None:
        @record(name="decorated-func", db_path=":memory:")
        def my_func(x: int) -> int:
            return x * 2

        result = my_func(5)
        assert result == 10

    def test_decorator_preserves_name(self) -> None:
        @record(name="test", db_path=":memory:")
        def my_func() -> str:
            return "hello"

        assert my_func.__name__ == "my_func"

    def test_decorator_uses_func_name_as_default(self) -> None:
        @record(db_path=":memory:")
        def my_agent_run() -> str:
            return "done"

        # The decorator should use the function name if no name is given
        result = my_agent_run()
        assert result == "done"
