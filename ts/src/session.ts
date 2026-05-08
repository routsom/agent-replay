/**
 * Session and Step data models for agent-replay TypeScript SDK.
 */

export interface Step {
  id: string;
  sessionId: string;
  sequence: number;
  type: 'llm_call' | 'tool_call' | 'tool_result' | 'reasoning' | 'message';
  startedAt: Date;
  endedAt?: Date;
  latencyMs?: number;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  error?: string;
  annotation?: string;
  verdict?: 'pass' | 'fail';
}

export interface Session {
  id: string;
  name?: string;
  framework: string;
  model: string;
  startedAt: Date;
  endedAt?: Date;
  status: 'running' | 'completed' | 'error';
  tags: string[];
  metadata: Record<string, unknown>;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalCostUsd: number;
  steps: Step[];
}

export interface DiffResult {
  sessionA: string;
  sessionB: string;
  stepsAdded: Step[];
  stepsRemoved: Step[];
  stepsChanged: [Step, Step][];
  costDeltaUsd: number;
  tokenDelta: number;
  summary: string;
}
