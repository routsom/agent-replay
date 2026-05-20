"""SQLite persistence layer for agent-replay.

Uses raw sqlite3 with parameterised queries — no ORM.
Schema migrations are versioned and applied on connection if PRAGMA user_version is behind.
Only stdlib imports allowed in this module.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_replay.session import Session, Step

logger = logging.getLogger("agent_replay")

# Current schema version — bump when adding migrations.
SCHEMA_VERSION = 1

# Initial schema creation.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT,
    framework TEXT NOT NULL,
    model TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    tags TEXT NOT NULL DEFAULT '[]',
    metadata TEXT NOT NULL DEFAULT '{}',
    total_input_tokens INTEGER NOT NULL DEFAULT 0,
    total_output_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost_usd REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS steps (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    latency_ms INTEGER,
    input TEXT NOT NULL DEFAULT '{}',
    output TEXT NOT NULL DEFAULT '{}',
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    error TEXT,
    annotation TEXT,
    verdict TEXT
);

CREATE INDEX IF NOT EXISTS idx_steps_session ON steps(session_id, sequence);
CREATE INDEX IF NOT EXISTS idx_sessions_framework ON sessions(framework);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
"""

# Ordered list of migrations. Index = version that migration upgrades TO.
# Migration 0 is the initial schema (applied via SCHEMA_SQL above).
MIGRATIONS: list[str] = [
    # Version 1 is the initial schema, no migration needed.
]


def _default_db_path() -> str:
    """Return the default database path, creating parent dirs if needed."""
    env_path = os.environ.get("AGENT_REPLAY_DB")
    if env_path:
        return env_path
    home = Path.home() / ".agent-replay"
    home.mkdir(parents=True, exist_ok=True)
    return str(home / "replay.db")


def _serialize(obj: object) -> str:
    """Serialize a value to JSON, handling datetimes and unknown types."""
    return json.dumps(obj, default=str)


def _deserialize(text: str) -> object:
    """Deserialize a JSON string, returning empty dict on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


class Store:
    """SQLite-backed persistence for sessions and steps."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or _default_db_path()
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create the database connection."""
        if self._conn is None:
            # Ensure parent directory exists for file-based DBs
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        """Create tables and run any pending migrations."""
        conn = self._conn
        assert conn is not None

        # Create initial schema
        conn.executescript(SCHEMA_SQL)

        # Check current version and apply migrations
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        for i in range(version, len(MIGRATIONS)):
            conn.executescript(MIGRATIONS[i])
            conn.execute(f"PRAGMA user_version = {i + 1}")
        conn.commit()

    def save_session(self, session: Session) -> None:
        """Insert or update a session record.

        Uses INSERT ... ON CONFLICT DO UPDATE instead of INSERT OR REPLACE
        to avoid triggering ON DELETE CASCADE on the steps table.
        """
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO sessions
               (id, name, framework, model, started_at, ended_at, status,
                tags, metadata, total_input_tokens, total_output_tokens, total_cost_usd)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                framework = excluded.framework,
                model = excluded.model,
                started_at = excluded.started_at,
                ended_at = excluded.ended_at,
                status = excluded.status,
                tags = excluded.tags,
                metadata = excluded.metadata,
                total_input_tokens = excluded.total_input_tokens,
                total_output_tokens = excluded.total_output_tokens,
                total_cost_usd = excluded.total_cost_usd""",
            (
                session.id,
                session.name,
                session.framework,
                session.model,
                session.started_at.isoformat(),
                session.ended_at.isoformat() if session.ended_at else None,
                session.status,
                _serialize(session.tags),
                _serialize(session.metadata),
                session.total_input_tokens,
                session.total_output_tokens,
                session.total_cost_usd,
            ),
        )
        conn.commit()

    def save_step(self, step: Step) -> None:
        """Insert or replace a step record."""
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO steps
               (id, session_id, sequence, type, started_at, ended_at, latency_ms,
                input, output, input_tokens, output_tokens, cost_usd, error,
                annotation, verdict)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                step.id,
                step.session_id,
                step.sequence,
                step.type,
                step.started_at.isoformat(),
                step.ended_at.isoformat() if step.ended_at else None,
                step.latency_ms,
                _serialize(step.input),
                _serialize(step.output),
                step.input_tokens,
                step.output_tokens,
                step.cost_usd,
                step.error,
                step.annotation,
                step.verdict,
            ),
        )
        conn.commit()

    def get_session(self, session_id: str, include_steps: bool = True) -> Session | None:
        """Retrieve a session by ID, optionally with its steps."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        session = self._row_to_session(row)
        if include_steps:
            session.steps = self.get_steps(session_id)
        return session

    def list_sessions(
        self,
        limit: int = 20,
        tag: str | None = None,
        framework: str | None = None,
    ) -> list[Session]:
        """List recent sessions with optional filters."""
        conn = self._get_conn()
        query = "SELECT * FROM sessions WHERE 1=1"
        params: list[object] = []

        if framework:
            query += " AND framework = ?"
            params.append(framework)

        if tag:
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [self._row_to_session(row) for row in rows]

    def get_steps(self, session_id: str) -> list[Step]:
        """Retrieve all steps for a session, ordered by sequence."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM steps WHERE session_id = ? ORDER BY sequence",
            (session_id,),
        ).fetchall()
        return [self._row_to_step(row) for row in rows]

    def update_annotation(
        self,
        session_id: str,
        step_id: str | None = None,
        note: str | None = None,
        verdict: str | None = None,
    ) -> None:
        """Attach an annotation and/or verdict to a session or step."""
        conn = self._get_conn()
        if step_id:
            if note is not None:
                conn.execute(
                    "UPDATE steps SET annotation = ? WHERE id = ? AND session_id = ?",
                    (note, step_id, session_id),
                )
            if verdict is not None:
                conn.execute(
                    "UPDATE steps SET verdict = ? WHERE id = ? AND session_id = ?",
                    (verdict, step_id, session_id),
                )
        else:
            # Annotate the session by storing in metadata
            session = self.get_session(session_id, include_steps=False)
            if session:
                meta: dict[str, Any] = dict(session.metadata) if session.metadata else {}
                if note is not None:
                    meta["annotation"] = note
                if verdict is not None:
                    meta["verdict"] = verdict
                conn.execute(
                    "UPDATE sessions SET metadata = ? WHERE id = ?",
                    (_serialize(meta), session_id),
                )
        conn.commit()

    def delete_session(self, session_id: str) -> None:
        """Delete a session and its steps (cascading)."""
        conn = self._get_conn()
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # --- Private helpers ---

    @staticmethod
    def _row_to_session(row: Any) -> Session:
        """Convert a raw DB row to a Session dataclass."""
        tags_raw = _deserialize(str(row[7]))
        tags = tags_raw if isinstance(tags_raw, list) else []
        metadata_raw = _deserialize(str(row[8]))
        metadata: dict[str, Any] = (
            {str(k): v for k, v in metadata_raw.items()} if isinstance(metadata_raw, dict) else {}
        )
        return Session(
            id=str(row[0]),
            name=str(row[1]) if row[1] else None,
            framework=str(row[2]),
            model=str(row[3]),
            started_at=datetime.fromisoformat(str(row[4])),
            ended_at=datetime.fromisoformat(str(row[5])) if row[5] else None,
            status=str(row[6]),
            tags=[str(t) for t in tags],
            metadata=metadata,
            total_input_tokens=int(row[9]) if row[9] else 0,
            total_output_tokens=int(row[10]) if row[10] else 0,
            total_cost_usd=float(row[11]) if row[11] else 0.0,
        )

    @staticmethod
    def _row_to_step(row: Any) -> Step:
        """Convert a raw DB row to a Step dataclass."""
        input_raw = _deserialize(str(row[7]))
        input_dict: dict[str, Any] = (
            {str(k): v for k, v in input_raw.items()} if isinstance(input_raw, dict) else {}
        )
        output_raw = _deserialize(str(row[8]))
        output_dict: dict[str, Any] = (
            {str(k): v for k, v in output_raw.items()} if isinstance(output_raw, dict) else {}
        )
        return Step(
            id=str(row[0]),
            session_id=str(row[1]),
            sequence=int(row[2]) if row[2] is not None else 0,
            type=str(row[3]),
            started_at=datetime.fromisoformat(str(row[4])),
            ended_at=datetime.fromisoformat(str(row[5])) if row[5] else None,
            latency_ms=int(row[6]) if row[6] is not None else None,
            input=input_dict,
            output=output_dict,
            input_tokens=int(row[9]) if row[9] is not None else 0,
            output_tokens=int(row[10]) if row[10] is not None else 0,
            cost_usd=float(row[11]) if row[11] is not None else 0.0,
            error=str(row[12]) if row[12] else None,
            annotation=str(row[13]) if row[13] else None,
            verdict=str(row[14]) if row[14] else None,
        )
