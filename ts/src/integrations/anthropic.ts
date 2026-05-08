/**
 * Anthropic integration for agent-replay TypeScript SDK.
 */

import { Recorder, StepContext } from '../recorder';
import { Session } from '../session';

export class ReplayClient {
  private recorder: Recorder;
  private client: any;
  public messages: ReplayMessages;

  constructor(client: any, options: { sessionName?: string; dbPath?: string } = {}) {
    this.client = client;
    this.recorder = new Recorder({
      name: options.sessionName,
      framework: 'anthropic',
      model: 'unknown',
      dbPath: options.dbPath,
    });
    this.recorder.start();
    this.messages = new ReplayMessages(client.messages, this.recorder);
  }

  async end(): Promise<void> {
    await this.recorder.end();
  }
}

class ReplayMessages {
  private messages: any;
  private recorder: Recorder;

  constructor(messages: any, recorder: Recorder) {
    this.messages = messages;
    this.recorder = recorder;
  }

  async create(params: any): Promise<any> {
    const model = params.model || 'unknown';
    if (this.recorder.session.model === 'unknown') {
      this.recorder.session.model = model;
    }

    const step = this.recorder.step('llm_call', {
      model,
      messages: params.messages,
      system: params.system,
      max_tokens: params.max_tokens,
    });

    try {
      const response = await this.messages.create(params);

      const output: Record<string, unknown> = {};
      if (response.content) {
        output.content = response.content.map((block: any) => ({
          type: block.type,
          text: block.text,
        }));
      }
      if (response.stop_reason) {
        output.stop_reason = response.stop_reason;
      }

      step.finish({
        output,
        inputTokens: response.usage?.input_tokens || 0,
        outputTokens: response.usage?.output_tokens || 0,
      });

      return response;
    } catch (e: any) {
      step.finish({ error: e.message || String(e) });
      throw e;
    }
  }
}
