"""CrewAI integration for agent-replay.

Provides a callback/wrapper that traces CrewAI crew runs.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_replay.recorder import Recorder

logger = logging.getLogger("agent_replay")


class ReplayCrewWrapper:
    """Wrapper that traces CrewAI crew executions.

    Usage::

        from agent_replay.integrations.crewai import ReplayCrewWrapper

        wrapper = ReplayCrewWrapper(session_name="my-crew")
        # Wrap your crew kickoff
        result = wrapper.trace_kickoff(crew)
        wrapper.end()
    """

    def __init__(
        self,
        session_name: str | None = None,
        model: str = "unknown",
        tags: list[str] | None = None,
        metadata: dict[str, object] | None = None,
        db_path: str | None = None,
    ) -> None:
        self._recorder = Recorder(
            name=session_name,
            framework="crewai",
            model=model,
            tags=tags,
            metadata=metadata,
            db_path=db_path,
        )
        self._recorder.__enter__()

    def trace_kickoff(self, crew: Any, **kwargs: Any) -> Any:
        """Trace a crew kickoff, recording the overall execution as a step.

        Args:
            crew: The CrewAI Crew instance to kick off.
            **kwargs: Passed through to crew.kickoff().

        Returns:
            The result of crew.kickoff().
        """
        step = self._recorder.step(
            "reasoning",
            input={
                "crew": getattr(crew, "name", str(type(crew).__name__)),
                "agents": [
                    getattr(a, "role", str(a)) for a in getattr(crew, "agents", [])
                ],
                "tasks": [
                    getattr(t, "description", str(t))[:100]
                    for t in getattr(crew, "tasks", [])
                ],
            },
        )

        try:
            result = crew.kickoff(**kwargs)

            output: dict[str, object] = {}
            if hasattr(result, "raw"):
                output["raw"] = str(result.raw)
            elif isinstance(result, str):
                output["result"] = result
            else:
                output["result"] = str(result)

            step.finish(output=output)
            return result

        except Exception as e:
            step.finish(error=str(e))
            raise

    def trace_task(self, task_name: str, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Trace a single task execution.

        Args:
            task_name: Human-readable task name.
            func: The callable to invoke.
            *args, **kwargs: Passed through to func.

        Returns:
            The return value of func.
        """
        step = self._recorder.step(
            "tool_call",
            input={"task": task_name},
        )

        try:
            result = func(*args, **kwargs)
            step.finish(output={"result": str(result)})
            return result
        except Exception as e:
            step.finish(error=str(e))
            raise

    def end(self) -> None:
        """End the recording session."""
        self._recorder.__exit__(None, None, None)

    def __enter__(self) -> ReplayCrewWrapper:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self._recorder.__exit__(exc_type, exc_val, exc_tb)
