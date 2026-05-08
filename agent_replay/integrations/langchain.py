"""LangChain callback handler integration for agent-replay.

Provides a callback handler that records LangChain chain/LLM runs as steps.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from agent_replay.recorder import Recorder, StepContext, _NoOpStepContext

logger = logging.getLogger("agent_replay")


class ReplayCallbackHandler:
    """LangChain callback handler that records all runs to agent-replay.

    Usage::

        from langchain_core.callbacks import CallbackManager
        from agent_replay.integrations.langchain import ReplayCallbackHandler

        handler = ReplayCallbackHandler(session_name="my-chain")
        chain = my_chain.with_config({"callbacks": [handler]})
        result = chain.invoke(...)
        handler.end()
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
            framework="langchain",
            model="unknown",
            tags=tags,
            metadata=metadata,
            db_path=db_path,
        )
        self._recorder.__enter__()
        self._active_steps: dict[str, StepContext | _NoOpStepContext] = {}

    def end(self) -> None:
        """End the recording session."""
        self._recorder.__exit__(None, None, None)

    # --- LLM callbacks ---

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Record start of an LLM call."""
        model = serialized.get("name", serialized.get("id", ["unknown"])[-1])
        if self._recorder.session.model == "unknown":
            self._recorder.session.model = model

        step = self._recorder.step(
            "llm_call",
            input={"model": model, "prompts": prompts},
        )
        self._active_steps[str(run_id)] = step

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        """Record completion of an LLM call."""
        step = self._active_steps.pop(str(run_id), None)
        if step is None:
            return

        output: dict[str, object] = {}
        input_tokens = 0
        output_tokens = 0

        if hasattr(response, "generations") and response.generations:
            output["generations"] = [
                [{"text": g.text} for g in gen] for gen in response.generations
            ]
        if hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            input_tokens = token_usage.get("prompt_tokens", 0)
            output_tokens = token_usage.get("completion_tokens", 0)

        step.finish(output=output, input_tokens=input_tokens, output_tokens=output_tokens)

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        """Record an LLM error."""
        step = self._active_steps.pop(str(run_id), None)
        if step:
            step.finish(error=str(error))

    # --- Tool callbacks ---

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Record start of a tool call."""
        step = self._recorder.step(
            "tool_call",
            input={"tool": serialized.get("name", "unknown"), "input": input_str},
        )
        self._active_steps[str(run_id)] = step

    def on_tool_end(self, output: str, *, run_id: UUID, **kwargs: Any) -> None:
        """Record completion of a tool call."""
        step = self._active_steps.pop(str(run_id), None)
        if step:
            step.finish(output={"result": output})

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        """Record a tool error."""
        step = self._active_steps.pop(str(run_id), None)
        if step:
            step.finish(error=str(error))

    # --- Chain callbacks (treated as reasoning steps) ---

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Record start of a chain execution."""
        step = self._recorder.step(
            "reasoning",
            input={"chain": serialized.get("name", "unknown"), "inputs": inputs},
        )
        self._active_steps[str(run_id)] = step

    def on_chain_end(self, outputs: dict[str, Any], *, run_id: UUID, **kwargs: Any) -> None:
        """Record completion of a chain execution."""
        step = self._active_steps.pop(str(run_id), None)
        if step:
            step.finish(output=outputs)

    def on_chain_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        """Record a chain error."""
        step = self._active_steps.pop(str(run_id), None)
        if step:
            step.finish(error=str(error))
