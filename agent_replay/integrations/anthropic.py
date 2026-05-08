"""Anthropic SDK integration for agent-replay.

Provides a ReplayClient wrapper that automatically traces all messages.create() calls.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_replay.recorder import Recorder

logger = logging.getLogger("agent_replay")


class _ReplayMessages:
    """Wrapper around anthropic.Anthropic().messages that records each call."""

    def __init__(self, messages: Any, recorder: Recorder) -> None:
        self._messages = messages
        self._recorder = recorder

    def create(self, **kwargs: Any) -> Any:
        """Intercept messages.create() and record the step."""
        model = kwargs.get("model", "unknown")
        if self._recorder.session.model == "unknown":
            self._recorder.session.model = model

        step = self._recorder.step(
            "llm_call",
            input={
                "model": model,
                "messages": kwargs.get("messages", []),
                "system": kwargs.get("system"),
                "max_tokens": kwargs.get("max_tokens"),
            },
        )

        try:
            response = self._messages.create(**kwargs)

            # Extract output
            output: dict[str, object] = {}
            if hasattr(response, "content") and response.content:
                output["content"] = [
                    {"type": getattr(block, "type", "text"), "text": getattr(block, "text", "")}
                    for block in response.content
                ]
            if hasattr(response, "stop_reason"):
                output["stop_reason"] = response.stop_reason

            # Extract tokens
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage"):
                input_tokens = getattr(response.usage, "input_tokens", 0)
                output_tokens = getattr(response.usage, "output_tokens", 0)

            step.finish(
                output=output,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            return response

        except Exception as e:
            step.finish(error=str(e))
            raise

    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to the underlying messages object."""
        return getattr(self._messages, name)


class ReplayClient:
    """Drop-in wrapper around anthropic.Anthropic() with automatic tracing.

    Usage::

        from anthropic import Anthropic
        from agent_replay.integrations.anthropic import ReplayClient

        client = ReplayClient(Anthropic(), session_name="customer-support")
        response = client.messages.create(model="claude-sonnet-4-6", ...)
    """

    def __init__(
        self,
        client: Any,
        session_name: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, object] | None = None,
        db_path: str | None = None,
    ) -> None:
        self._client = client
        self._recorder = Recorder(
            name=session_name,
            framework="anthropic",
            model="unknown",  # Will be set on first call
            tags=tags,
            metadata=metadata,
            db_path=db_path,
        )
        self._recorder.__enter__()
        self.messages = _ReplayMessages(client.messages, self._recorder)

    def end(self) -> None:
        """End the recording session."""
        self._recorder.__exit__(None, None, None)

    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to the underlying client."""
        return getattr(self._client, name)

    def __enter__(self) -> ReplayClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self._recorder.__exit__(exc_type, exc_val, exc_tb)
