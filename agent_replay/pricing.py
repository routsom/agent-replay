"""Pricing manifest loader for agent-replay.

Loads the YAML pricing manifest and provides it as a nested dict.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, cast

import yaml

logger = logging.getLogger("agent_replay")

_pricing_cache: dict[str, object] | None = None


def _bundled_manifest_path() -> str:
    """Return the path to the bundled pricing/models.yaml."""
    return str(Path(__file__).parent.parent / "pricing" / "models.yaml")


def load_pricing(path: str | None = None) -> dict[str, dict[str, dict[str, float]]]:
    """Load the pricing manifest from YAML.

    Resolution order:
    1. Explicit ``path`` argument
    2. ``AGENT_REPLAY_PRICING`` environment variable
    3. Bundled ``pricing/models.yaml``

    Returns a dict of ``{provider: {model: {input_per_million, output_per_million}}}``.
    """
    global _pricing_cache  # noqa: PLW0603
    if _pricing_cache is not None and path is None:
        return _pricing_cache  # type: ignore[return-value]

    manifest_path = path or os.environ.get("AGENT_REPLAY_PRICING") or _bundled_manifest_path()

    try:
        with open(manifest_path) as f:
            raw: Any = cast(Any, yaml.safe_load(f))
    except FileNotFoundError:
        logger.warning("agent-replay: pricing manifest not found at %s", manifest_path)
        return {}
    except yaml.YAMLError as e:
        logger.warning("agent-replay: failed to parse pricing manifest: %s", e)
        return {}

    if not isinstance(raw, dict):
        logger.warning("agent-replay: pricing manifest has unexpected structure")
        return {}

    providers: dict[str, dict[str, dict[str, float]]] = raw.get("providers", {})

    if path is None:
        _pricing_cache = providers  # type: ignore[assignment]

    return providers


def reset_pricing_cache() -> None:
    """Clear the cached pricing data (useful for testing)."""
    global _pricing_cache  # noqa: PLW0603
    _pricing_cache = None
