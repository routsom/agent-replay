"""Google ADK integration for agent-replay.

Provides a tracing wrapper for Google ADK agent runs.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_replay.recorder import Recorder

logger = logging.getLogger("agent_replay")


class ReplayADKWrapper:
    """Wrapper that traces Google ADK agent invocations.

    Usage::

        from agent_replay.integrations.google_adk import ReplayADKWrapper

        wrapper = ReplayADKWrapper(session_name="my-adk-agent")
        result = wrapper.trace_call(
            func=agent.generate_content,
            model="gemini-2.0-flash-exp",
            input_data={"prompt": "Hello"},
        )
        wrapper.end()
    """

    def __init__(
        self,
        session_name: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, object] | None = None,
        db_path: str | None = None,
    ) -> None:
        self._recorder = Recorder(
            name=session_name,
            framework="google_adk",
            model="unknown",
            tags=tags,
            metadata=metadata,
            db_path=db_path,
        )
        self._recorder.__enter__()

    def trace_call(
        self,
        func: Any,
        model: str = "unknown",
        input_data: dict[str, object] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Trace a single ADK function call.

        Args:
            func: The callable to invoke (e.g. agent.generate_content).
            model: Model name for cost tracking.
            input_data: Input to record.
            **kwargs: Passed through to func.

        Returns:
            The return value of func.
        """
        if self._recorder.session.model == "unknown":
            self._recorder.session.model = model

        step = self._recorder.step(
            "llm_call",
            input={"model": model, **(input_data or {})},
        )

        try:
            result = func(**kwargs)

            output: dict[str, object] = {}
            input_tokens = 0
            output_tokens = 0

            # Try to extract token usage from common ADK response shapes
            if hasattr(result, "text"):
                output["text"] = result.text
            if hasattr(result, "usage_metadata"):
                usage = result.usage_metadata
                input_tokens = getattr(usage, "prompt_token_count", 0) or 0
                output_tokens = getattr(usage, "candidates_token_count", 0) or 0

            step.finish(
                output=output,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            return result

        except Exception as e:
            step.finish(error=str(e))
            raise

    def end(self) -> None:
        """End the recording session."""
        self._recorder.__exit__(None, None, None)

    def __enter__(self) -> ReplayADKWrapper:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self._recorder.__exit__(exc_type, exc_val, exc_tb)
