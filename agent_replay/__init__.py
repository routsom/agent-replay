"""agent-replay — Dead-simple, local-first agent observability.

Public API surface. If it's not here, it's internal.
"""

from agent_replay.recorder import Recorder, record, record_if
from agent_replay.session import DiffResult, Session, Step

__all__ = [
    "Recorder",
    "record",
    "record_if",
    "Session",
    "Step",
    "DiffResult",
]

__version__ = "0.1.0"
