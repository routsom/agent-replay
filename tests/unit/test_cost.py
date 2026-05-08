"""Unit tests for cost.py — Token cost calculator."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent_replay.cost import calculate_cost
from agent_replay.pricing import reset_pricing_cache


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear pricing cache before each test."""
    reset_pricing_cache()


class TestCalculateCost:
    def test_anthropic_sonnet_cost(self) -> None:
        # claude-sonnet-4-6: $3.00 in / $15.00 out per million
        cost = calculate_cost(
            model="claude-sonnet-4-6",
            provider="anthropic",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        assert cost == pytest.approx(18.00)

    def test_anthropic_opus_cost(self) -> None:
        # claude-opus-4-6: $15.00 in / $75.00 out per million
        cost = calculate_cost(
            model="claude-opus-4-6",
            provider="anthropic",
            input_tokens=1_000,
            output_tokens=1_000,
        )
        expected = (1_000 / 1_000_000) * 15.00 + (1_000 / 1_000_000) * 75.00
        assert cost == pytest.approx(expected)

    def test_anthropic_haiku_cost(self) -> None:
        cost = calculate_cost(
            model="claude-haiku-4-5-20251001",
            provider="anthropic",
            input_tokens=500_000,
            output_tokens=500_000,
        )
        expected = (500_000 / 1_000_000) * 0.80 + (500_000 / 1_000_000) * 4.00
        assert cost == pytest.approx(expected)

    def test_openai_gpt4o_cost(self) -> None:
        cost = calculate_cost(
            model="gpt-4o",
            provider="openai",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        assert cost == pytest.approx(12.50)

    def test_openai_gpt4o_mini_cost(self) -> None:
        cost = calculate_cost(
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        assert cost == pytest.approx(0.75)

    def test_google_gemini_cost(self) -> None:
        cost = calculate_cost(
            model="gemini-2.0-flash-exp",
            provider="google",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        assert cost == pytest.approx(0.375)

    def test_unknown_model_returns_zero(self) -> None:
        cost = calculate_cost(
            model="nonexistent-model",
            provider="anthropic",
            input_tokens=1000,
            output_tokens=1000,
        )
        assert cost == 0.0

    def test_unknown_provider_returns_zero(self) -> None:
        cost = calculate_cost(
            model="some-model",
            provider="nonexistent-provider",
            input_tokens=1000,
            output_tokens=1000,
        )
        assert cost == 0.0

    def test_zero_tokens(self) -> None:
        cost = calculate_cost(
            model="claude-sonnet-4-6",
            provider="anthropic",
            input_tokens=0,
            output_tokens=0,
        )
        assert cost == 0.0

    def test_input_only(self) -> None:
        cost = calculate_cost(
            model="claude-sonnet-4-6",
            provider="anthropic",
            input_tokens=1_000_000,
            output_tokens=0,
        )
        assert cost == pytest.approx(3.00)

    def test_output_only(self) -> None:
        cost = calculate_cost(
            model="claude-sonnet-4-6",
            provider="anthropic",
            input_tokens=0,
            output_tokens=1_000_000,
        )
        assert cost == pytest.approx(15.00)
