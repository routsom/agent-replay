"""Diff engine for agent-replay.

Compares two sessions by matching steps on sequence number and computing deltas.
"""

from __future__ import annotations

import json

from agent_replay.session import DiffResult, Step
from agent_replay.store import Store


def _steps_differ(a: Step, b: Step) -> bool:
    """Check whether two steps differ in meaningful ways."""
    return (
        a.type != b.type
        or json.dumps(a.input, default=str, sort_keys=True)
        != json.dumps(b.input, default=str, sort_keys=True)
        or json.dumps(a.output, default=str, sort_keys=True)
        != json.dumps(b.output, default=str, sort_keys=True)
        or a.input_tokens != b.input_tokens
        or a.output_tokens != b.output_tokens
        or a.error != b.error
    )


def diff_sessions(
    session_a_id: str,
    session_b_id: str,
    store: Store | None = None,
) -> DiffResult:
    """Compare two recorded sessions and return a structured diff.

    Steps are matched by their sequence number. Steps present in B but
    not in A are marked as added; steps in A but not B are removed.
    Matching steps that differ are listed as changed.

    Args:
        session_a_id: The ID of the first (baseline) session.
        session_b_id: The ID of the second (comparison) session.
        store: Optional Store instance. Uses default DB if not provided.

    Returns:
        A DiffResult summarizing all differences.
    """
    _store = store or Store()
    try:
        session_a = _store.get_session(session_a_id, include_steps=True)
        session_b = _store.get_session(session_b_id, include_steps=True)

        if session_a is None:
            raise ValueError(f"Session not found: {session_a_id}")
        if session_b is None:
            raise ValueError(f"Session not found: {session_b_id}")

        steps_a = {s.sequence: s for s in session_a.steps}
        steps_b = {s.sequence: s for s in session_b.steps}

        all_seqs = sorted(set(steps_a.keys()) | set(steps_b.keys()))

        added: list[Step] = []
        removed: list[Step] = []
        changed: list[tuple[Step, Step]] = []

        for seq in all_seqs:
            in_a = seq in steps_a
            in_b = seq in steps_b

            if in_a and not in_b:
                removed.append(steps_a[seq])
            elif in_b and not in_a:
                added.append(steps_b[seq])
            elif in_a and in_b:
                a_step = steps_a[seq]
                b_step = steps_b[seq]
                if _steps_differ(a_step, b_step):
                    changed.append((a_step, b_step))

        cost_delta = session_b.total_cost_usd - session_a.total_cost_usd
        token_delta = (
            (session_b.total_input_tokens + session_b.total_output_tokens)
            - (session_a.total_input_tokens + session_a.total_output_tokens)
        )

        parts = []
        if added:
            parts.append(f"{len(added)} added")
        if removed:
            parts.append(f"{len(removed)} removed")
        if changed:
            parts.append(f"{len(changed)} changed")
        if not parts:
            parts.append("no differences")
        summary = f"Steps: {', '.join(parts)}. Cost delta: ${cost_delta:+.4f}."

        return DiffResult(
            session_a=session_a_id,
            session_b=session_b_id,
            steps_added=added,
            steps_removed=removed,
            steps_changed=changed,
            cost_delta_usd=cost_delta,
            token_delta=token_delta,
            summary=summary,
        )
    finally:
        if store is None:
            _store.close()
