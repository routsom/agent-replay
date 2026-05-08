/**
 * Core Recorder class for agent-replay TypeScript SDK.
 */

import { v4 as uuidv4 } from 'uuid';
import { Session, Step } from './session';
import { Store } from './store';
import { calculateCost } from './cost';

export interface RecorderOptions {
  name?: string;
  framework?: string;
  model?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
  dbPath?: string;
}

export class StepContext {
  public step: Step;
  private recorder: Recorder;

  constructor(recorder: Recorder, stepType: Step['type'], input?: Record<string, unknown>) {
    this.recorder = recorder;
    this.step = {
      id: uuidv4(),
      sessionId: recorder.session.id,
      sequence: recorder.nextSequence(),
      type: stepType,
      startedAt: new Date(),
      input: input || {},
      output: {},
      inputTokens: 0,
      outputTokens: 0,
      costUsd: 0,
    };
  }

  finish(options: {
    output?: Record<string, unknown>;
    inputTokens?: number;
    outputTokens?: number;
    error?: string;
  } = {}): Step {
    this.step.endedAt = new Date();
    this.step.output = options.output || {};
    this.step.inputTokens = options.inputTokens || 0;
    this.step.outputTokens = options.outputTokens || 0;
    this.step.error = options.error;

    this.step.latencyMs = this.step.endedAt.getTime() - this.step.startedAt.getTime();

    this.step.costUsd = calculateCost(
      this.recorder.session.model,
      this.recorder.session.framework,
      this.step.inputTokens,
      this.step.outputTokens,
    );

    this.recorder.session.totalInputTokens += this.step.inputTokens;
    this.recorder.session.totalOutputTokens += this.step.outputTokens;
    this.recorder.session.totalCostUsd += this.step.costUsd;

    try {
      this.recorder.store.saveStep(this.step);
    } catch (e) {
      console.warn(`agent-replay: failed to save step: ${e}`);
    }

    return this.step;
  }
}

export class Recorder {
  public session: Session;
  public store: Store;
  private sequenceCounter = 0;

  constructor(options: RecorderOptions = {}) {
    this.store = new Store(options.dbPath);
    this.session = {
      id: uuidv4(),
      name: options.name,
      framework: options.framework || 'custom',
      model: options.model || 'unknown',
      startedAt: new Date(),
      status: 'running',
      tags: options.tags || [],
      metadata: options.metadata || {},
      totalInputTokens: 0,
      totalOutputTokens: 0,
      totalCostUsd: 0,
      steps: [],
    };
  }

  nextSequence(): number {
    return this.sequenceCounter++;
  }

  async start(): Promise<Session> {
    try {
      this.store.saveSession(this.session);
    } catch (e) {
      console.warn(`agent-replay: failed to save session: ${e}`);
    }
    return this.session;
  }

  step(stepType: Step['type'], input?: Record<string, unknown>): StepContext {
    return new StepContext(this, stepType, input);
  }

  async end(status: Session['status'] = 'completed'): Promise<void> {
    this.session.endedAt = new Date();
    this.session.status = status;
    try {
      this.store.saveSession(this.session);
    } catch (e) {
      console.warn(`agent-replay: failed to finalize session: ${e}`);
    }
    this.store.close();
  }
}
