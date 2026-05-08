"""Integration tests for the Anthropic integration."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent_replay.integrations.anthropic import ReplayClient
from agent_replay.store import Store


def _mock_anthropic_response() -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Hello! How can I help?")],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=25, output_tokens=40),
    )


class TestAnthropicIntegration:
    def test_replay_client_traces_call(self) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response()

        with ReplayClient(
            mock_client, session_name="test", db_path=":memory:"
        ) as client:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": "Hello"}],
            )

        assert response.content[0].text == "Hello! How can I help?"
        mock_client.messages.create.assert_called_once()

    def test_replay_client_records_tokens(self) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response()

        client = ReplayClient(mock_client, session_name="test", db_path=":memory:")
        client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Hi"}],
        )
        client.end()

        assert client._recorder.session.total_input_tokens == 25
        assert client._recorder.session.total_output_tokens == 40

    def test_replay_client_handles_error(self) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API Error")

        client = ReplayClient(mock_client, session_name="test", db_path=":memory:")

        with pytest.raises(RuntimeError, match="API Error"):
            client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": "Hi"}],
            )

        client.end()
        assert client._recorder.session.status == "completed"  # Client itself didn't error

    def test_replay_client_proxy(self) -> None:
        mock_client = MagicMock()
        mock_client.api_key = "test-key"

        client = ReplayClient(mock_client, session_name="test", db_path=":memory:")
        assert client.api_key == "test-key"
        client.end()
