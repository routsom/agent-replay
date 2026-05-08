"""Replay engine for agent-replay.

Re-executes a recorded session against a (possibly different) model,
saving the result as a new session linked to the original via metadata.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from agent_replay.session import Session, Step
from agent_replay.store import Store

logger = logging.getLogger("agent_replay")


def replay_session(
    session_id: str,
    model_override: str | None = None,
    dry_run: bool = False,
    store: Store | None = None,
) -> Session | None:
    """Re-execute a recorded session, optionally against a different model.

    Args:
        session_id: The ID of the session to replay.
        model_override: If set, uses this model instead of the original.
        dry_run: If True, prints the plan without executing.
        store: Optional Store instance.

    Returns:
        The new Session if executed, or None for dry runs.
    """
    _store = store or Store()
    try:
        original = _store.get_session(session_id, include_steps=True)
        if original is None:
            raise ValueError(f"Session not found: {session_id}")

        target_model = model_override or original.model

        if dry_run:
            _print_plan(original, target_model)
            return None

        # Create a new session linked to the original
        new_session = Session(
            id=str(uuid.uuid4()),
            name=f"replay-of-{original.name or original.id[:8]}",
            framework=original.framework,
            model=target_model,
            started_at=datetime.now(),
            tags=original.tags + ["replay"],
            metadata={
                "replayed_from": original.id,
                "original_model": original.model,
            },
        )
        _store.save_session(new_session)

        # Replay each step — for now, copy the structure.
        # Actual LLM re-execution requires integration-specific logic
        # that would be added per integration.
        for step in original.steps:
            new_step = Step(
                id=str(uuid.uuid4()),
                session_id=new_session.id,
                sequence=step.sequence,
                type=step.type,
                started_at=datetime.now(),
                input=step.input,
                output=step.output,  # Will be replaced by actual call in integration replays
                input_tokens=step.input_tokens,
                output_tokens=step.output_tokens,
                cost_usd=step.cost_usd,
            )
            new_step.ended_at = datetime.now()
            if new_step.ended_at and new_step.started_at:
                delta = new_step.ended_at - new_step.started_at
                new_step.latency_ms = int(delta.total_seconds() * 1000)

            new_session.total_input_tokens += new_step.input_tokens
            new_session.total_output_tokens += new_step.output_tokens
            new_session.total_cost_usd += new_step.cost_usd
            new_session.steps.append(new_step)

            _store.save_step(new_step)

        # Finalize the new session
        new_session.ended_at = datetime.now()
        new_session.status = "completed"
        _store.save_session(new_session)

        return new_session

    finally:
        if store is None:
            _store.close()


def _print_plan(session: Session, target_model: str) -> None:
    """Print the replay plan without executing."""
    print(f"Replay Plan for session {session.id}")
    print(f"  Original model: {session.model}")
    print(f"  Target model:   {target_model}")
    print(f"  Framework:      {session.framework}")
    print(f"  Steps to replay: {len(session.steps)}")
    print()
    for step in session.steps:
        print(f"  [{step.sequence}] {step.type}")
        print(f"       Input:  {json.dumps(step.input, default=str)[:120]}")
        print(f"       Tokens: {step.input_tokens} in / {step.output_tokens} out")
        print()
