"""OpenAI SDK integration for agent-replay.

Provides a ReplayClient wrapper that automatically traces all chat.completions.create() calls.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_replay.recorder import Recorder

logger = logging.getLogger("agent_replay")


class _ReplayCompletions:
    """Wrapper around openai.OpenAI().chat.completions that records each call."""

    def __init__(self, completions: Any, recorder: Recorder) -> None:
        self._completions = completions
        self._recorder = recorder

    def create(self, **kwargs: Any) -> Any:
        """Intercept chat.completions.create() and record the step."""
        model = kwargs.get("model", "unknown")
        if self._recorder.session.model == "unknown":
            self._recorder.session.model = model

        step = self._recorder.step(
            "llm_call",
            input={
                "model": model,
                "messages": kwargs.get("messages", []),
                "temperature": kwargs.get("temperature"),
                "max_tokens": kwargs.get("max_tokens"),
            },
        )

        try:
            response = self._completions.create(**kwargs)

            output: dict[str, object] = {}
            if hasattr(response, "choices") and response.choices:
                choice = response.choices[0]
                if hasattr(choice, "message"):
                    output["content"] = getattr(choice.message, "content", "")
                    output["role"] = getattr(choice.message, "role", "assistant")
                output["finish_reason"] = getattr(choice, "finish_reason", None)

            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage") and response.usage:
                input_tokens = getattr(response.usage, "prompt_tokens", 0)
                output_tokens = getattr(response.usage, "completion_tokens", 0)

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
        return getattr(self._completions, name)


class _ReplayChat:
    """Wrapper around openai.OpenAI().chat."""

    def __init__(self, chat: Any, recorder: Recorder) -> None:
        self._chat = chat
        self.completions = _ReplayCompletions(chat.completions, recorder)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)


class ReplayClient:
    """Drop-in wrapper around openai.OpenAI() with automatic tracing.

    Usage::

        from openai import OpenAI
        from agent_replay.integrations.openai import ReplayClient

        client = ReplayClient(OpenAI(), session_name="my-chatbot")
        response = client.chat.completions.create(model="gpt-4o", ...)
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
            framework="openai",
            model="unknown",
            tags=tags,
            metadata=metadata,
            db_path=db_path,
        )
        self._recorder.__enter__()
        self.chat = _ReplayChat(client.chat, self._recorder)

    def end(self) -> None:
        """End the recording session."""
        self._recorder.__exit__(None, None, None)

    def __getattr__(self, name: str) -> Any:
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
