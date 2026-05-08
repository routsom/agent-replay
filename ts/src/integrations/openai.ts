/**
 * OpenAI integration for agent-replay TypeScript SDK.
 */

import { Recorder } from '../recorder';

export class ReplayClient {
  private recorder: Recorder;
  private client: any;
  public chat: { completions: ReplayCompletions };

  constructor(client: any, options: { sessionName?: string; dbPath?: string } = {}) {
    this.client = client;
    this.recorder = new Recorder({
      name: options.sessionName,
      framework: 'openai',
      model: 'unknown',
      dbPath: options.dbPath,
    });
    this.recorder.start();
    this.chat = {
      completions: new ReplayCompletions(client.chat.completions, this.recorder),
    };
  }

  async end(): Promise<void> {
    await this.recorder.end();
  }
}

class ReplayCompletions {
  private completions: any;
  private recorder: Recorder;

  constructor(completions: any, recorder: Recorder) {
    this.completions = completions;
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
      temperature: params.temperature,
      max_tokens: params.max_tokens,
    });

    try {
      const response = await this.completions.create(params);

      const output: Record<string, unknown> = {};
      if (response.choices?.[0]) {
        const choice = response.choices[0];
        output.content = choice.message?.content;
        output.role = choice.message?.role;
        output.finish_reason = choice.finish_reason;
      }

      step.finish({
        output,
        inputTokens: response.usage?.prompt_tokens || 0,
        outputTokens: response.usage?.completion_tokens || 0,
      });

      return response;
    } catch (e: any) {
      step.finish({ error: e.message || String(e) });
      throw e;
    }
  }
}
