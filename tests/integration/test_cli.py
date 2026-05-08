"""Integration tests for the CLI."""

from __future__ import annotations

from datetime import datetime

import pytest
from typer.testing import CliRunner

from agent_replay.cli.main import app
from agent_replay.session import Session, Step
from agent_replay.store import Store

runner = CliRunner()


@pytest.fixture
def db_path(tmp_path: object) -> str:
    return str(tmp_path) + "/test.db"  # type: ignore[operator]


@pytest.fixture
def seeded_db(db_path: str) -> str:
    store = Store(db_path=db_path)
    session = Session(
        id="cli-test-001", name="cli-test", framework="anthropic",
        model="claude-sonnet-4-6", started_at=datetime(2026, 5, 1),
        ended_at=datetime(2026, 5, 1, 0, 1), status="completed",
        tags=["test"], total_input_tokens=100, total_output_tokens=200,
        total_cost_usd=0.005,
    )
    store.save_session(session)
    step = Step(
        id="cli-step-001", session_id="cli-test-001", sequence=0,
        type="llm_call", started_at=datetime(2026, 5, 1),
        input={"prompt": "hello"}, output={"text": "hi"},
        input_tokens=50, output_tokens=100, cost_usd=0.002,
    )
    store.save_step(step)
    store.close()
    return db_path


class TestCLI:
    def test_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "agent-replay" in result.output.lower() or "replay" in result.output.lower()

    def test_list(self, seeded_db: str) -> None:
        result = runner.invoke(app, ["list", "--db", seeded_db])
        assert result.exit_code == 0

    def test_list_json(self, seeded_db: str) -> None:
        result = runner.invoke(app, ["list", "--db", seeded_db, "--json"])
        assert result.exit_code == 0
        assert "cli-test-001" in result.output

    def test_show(self, seeded_db: str) -> None:
        result = runner.invoke(app, ["show", "cli-test-001", "--db", seeded_db])
        assert result.exit_code == 0

    def test_show_json(self, seeded_db: str) -> None:
        result = runner.invoke(app, ["show", "cli-test-001", "--db", seeded_db, "--json"])
        assert result.exit_code == 0
        assert "cli-test-001" in result.output

    def test_show_steps(self, seeded_db: str) -> None:
        result = runner.invoke(app, ["show", "cli-test-001", "--steps", "--db", seeded_db])
        assert result.exit_code == 0

    def test_show_nonexistent(self, seeded_db: str) -> None:
        result = runner.invoke(app, ["show", "nonexistent", "--db", seeded_db])
        assert result.exit_code == 1

    def test_annotate(self, seeded_db: str) -> None:
        result = runner.invoke(app, [
            "annotate", "cli-test-001", "--note", "Good run", "--db", seeded_db
        ])
        assert result.exit_code == 0
        assert "Annotated" in result.output

    def test_annotate_with_verdict(self, seeded_db: str) -> None:
        result = runner.invoke(app, [
            "annotate", "cli-test-001", "--note", "Pass",
            "--verdict", "pass", "--db", seeded_db
        ])
        assert result.exit_code == 0

    def test_export_jsonl(self, seeded_db: str) -> None:
        result = runner.invoke(app, [
            "export", "cli-test-001", "--format", "jsonl", "--db", seeded_db
        ])
        assert result.exit_code == 0
        assert "cli-test-001" in result.output

    def test_export_html(self, seeded_db: str) -> None:
        result = runner.invoke(app, [
            "export", "cli-test-001", "--format", "html", "--db", seeded_db
        ])
        assert result.exit_code == 0
        assert "<!DOCTYPE html>" in result.output

    def test_replay_dry_run(self, seeded_db: str) -> None:
        result = runner.invoke(app, [
            "replay", "cli-test-001", "--dry-run", "--db", seeded_db
        ])
        assert result.exit_code == 0

    def test_stats(self, seeded_db: str) -> None:
        result = runner.invoke(app, ["stats", "--db", seeded_db])
        assert result.exit_code == 0
