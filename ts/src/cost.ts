/**
 * Token cost calculator for agent-replay TypeScript SDK.
 */

import * as fs from 'fs';
import * as path from 'path';

interface ModelPricing {
  input_per_million: number;
  output_per_million: number;
}

type PricingManifest = Record<string, Record<string, ModelPricing>>;

let cachedPricing: PricingManifest | null = null;

function loadPricing(): PricingManifest {
  if (cachedPricing) return cachedPricing;

  const manifestPath = process.env.AGENT_REPLAY_PRICING
    || path.join(__dirname, '..', '..', 'pricing', 'models.yaml');

  try {
    // Simple YAML parser for our flat structure
    const content = fs.readFileSync(manifestPath, 'utf-8');
    const pricing: PricingManifest = {};
    let currentProvider = '';
    let currentModel = '';

    for (const line of content.split('\n')) {
      const trimmed = line.trimEnd();
      if (trimmed.startsWith('#') || !trimmed) continue;

      const indent = line.length - line.trimStart().length;

      if (indent === 2 && trimmed.endsWith(':') && !trimmed.includes('version')) {
        currentProvider = trimmed.trim().replace(':', '');
        pricing[currentProvider] = {};
      } else if (indent === 4 && trimmed.endsWith(':')) {
        currentModel = trimmed.trim().replace(':', '');
        pricing[currentProvider][currentModel] = { input_per_million: 0, output_per_million: 0 };
      } else if (indent === 6 && trimmed.includes(':')) {
        const [key, value] = trimmed.trim().split(':').map(s => s.trim());
        if (pricing[currentProvider]?.[currentModel]) {
          (pricing[currentProvider][currentModel] as any)[key] = parseFloat(value);
        }
      }
    }

    cachedPricing = pricing;
    return pricing;
  } catch {
    console.warn('agent-replay: failed to load pricing manifest');
    return {};
  }
}

export function calculateCost(
  model: string,
  provider: string,
  inputTokens: number,
  outputTokens: number,
): number {
  const pricing = loadPricing();

  const providerPricing = pricing[provider];
  if (!providerPricing) {
    console.warn(`agent-replay: unknown provider '${provider}'`);
    return 0;
  }

  const modelPricing = providerPricing[model];
  if (!modelPricing) {
    console.warn(`agent-replay: unknown model '${provider}/${model}'`);
    return 0;
  }

  const inputCost = (inputTokens / 1_000_000) * modelPricing.input_per_million;
  const outputCost = (outputTokens / 1_000_000) * modelPricing.output_per_million;

  return inputCost + outputCost;
}
