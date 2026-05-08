# Pricing

agent-replay calculates per-step and per-session costs using a bundled pricing manifest.

## Current Prices (2026-05)

### Anthropic

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| claude-opus-4-6 | $15.00 | $75.00 |
| claude-sonnet-4-6 | $3.00 | $15.00 |
| claude-haiku-4-5-20251001 | $0.80 | $4.00 |

### OpenAI

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |

### Google

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| gemini-2.0-flash-exp | $0.075 | $0.30 |

## Custom Pricing

Override the bundled manifest by setting:

```bash
export AGENT_REPLAY_PRICING=/path/to/your/models.yaml
```

### Format

```yaml
version: "2026-05"
providers:
  your_provider:
    your-model-name:
      input_per_million: 1.00
      output_per_million: 5.00
```

## Unknown Models

If a model is not in the pricing manifest, cost is reported as `$0.00` and a warning is logged. Tracing continues normally.

## Updating Prices

1. Edit `pricing/models.yaml`
2. Bump the `version` field
3. Run `pytest tests/unit/test_cost.py` to verify
