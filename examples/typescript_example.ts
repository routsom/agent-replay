/**
 * Example: TypeScript SDK usage with agent-replay.
 *
 * Usage:
 *   npm install agent-replay @anthropic-ai/sdk
 *   npx ts-node examples/typescript_example.ts
 */

import { Recorder } from 'agent-replay';

async function main() {
  const recorder = new Recorder({
    name: 'typescript-example',
    framework: 'anthropic',
    model: 'claude-sonnet-4-6',
    tags: ['example', 'typescript'],
  });

  await recorder.start();

  // Simulate an LLM call
  const step = recorder.step('llm_call', {
    prompt: 'What is the capital of France?',
  });

  // ... In a real app, you'd call the actual API here ...

  step.finish({
    output: { text: 'The capital of France is Paris.' },
    inputTokens: 15,
    outputTokens: 25,
  });

  await recorder.end();

  console.log(`✅ Session ${recorder.session.id} recorded!`);
  console.log(`   Tokens: ${recorder.session.totalInputTokens} in / ${recorder.session.totalOutputTokens} out`);
  console.log(`   Cost: $${recorder.session.totalCostUsd.toFixed(4)}`);
}

main().catch(console.error);
