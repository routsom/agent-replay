"""Session and Step data models for agent-replay.

These are the canonical types. Everything else depends on them.
Only stdlib imports allowed in this module.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Step:
    """A single step within an agent session (LLM call, tool call, etc.)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    sequence: int = 0
    type: str = "llm_call"  # "llm_call" | "tool_call" | "tool_result" | "reasoning" | "message"
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None
    latency_ms: int | None = None
    input: dict[str, object] = field(default_factory=dict)
    output: dict[str, object] = field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    annotation: str | None = None
    verdict: str | None = None  # "pass" | "fail" | None


@dataclass
class Session:
    """A recorded agent session containing one or more steps."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str | None = None
    framework: str = "custom"  # e.g. anthropic, openai, langchain, crewai
    model: str = "unknown"
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None
    status: str = "running"  # "running" | "completed" | "error"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    steps: list[Step] = field(default_factory=list)  # populated on read, not stored inline


@dataclass
class DiffResult:
    """Result of comparing two sessions."""

    session_a: str = ""  # session ID
    session_b: str = ""
    steps_added: list[Step] = field(default_factory=list)  # in B but not A
    steps_removed: list[Step] = field(default_factory=list)  # in A but not B
    steps_changed: list[tuple[Step, Step]] = field(default_factory=list)  # (a_step, b_step) pairs
    cost_delta_usd: float = 0.0
    token_delta: int = 0
    summary: str = ""  # human-readable one-liner
