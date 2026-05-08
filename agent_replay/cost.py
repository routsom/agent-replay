"""Token cost calculator for agent-replay.

Uses the pricing manifest to compute costs per step.
Never raises — returns 0.0 for unknown models with a warning.
"""

from __future__ import annotations

import logging

from agent_replay.pricing import load_pricing

logger = logging.getLogger("agent_replay")


def calculate_cost(
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Calculate the USD cost for a given model call.

    Args:
        model: Model name as returned by the provider (e.g. "claude-sonnet-4-6").
        provider: Provider key (e.g. "anthropic", "openai", "google").
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.

    Returns:
        Cost in USD. Returns 0.0 if the model is not in the pricing manifest.
    """
    pricing = load_pricing()

    provider_pricing = pricing.get(provider)
    if not provider_pricing:
        logger.warning(
            "agent-replay: unknown provider '%s' — cost will be $0.00",
            provider,
        )
        return 0.0

    model_pricing = provider_pricing.get(model)
    if not model_pricing:
        logger.warning(
            "agent-replay: unknown model '%s/%s' — cost will be $0.00",
            provider,
            model,
        )
        return 0.0

    input_cost = (input_tokens / 1_000_000) * model_pricing.get("input_per_million", 0.0)
    output_cost = (output_tokens / 1_000_000) * model_pricing.get("output_per_million", 0.0)

    return input_cost + output_cost
