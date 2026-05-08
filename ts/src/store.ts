/**
 * SQLite persistence layer for agent-replay TypeScript SDK.
 * Uses better-sqlite3 (synchronous).
 */

import Database from 'better-sqlite3';
import * as path from 'path';
import * as os from 'os';
import * as fs from 'fs';
import { Session, Step } from './session';

const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT,
    framework TEXT NOT NULL,
    model TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    tags TEXT NOT NULL DEFAULT '[]',
    metadata TEXT NOT NULL DEFAULT '{}',
    total_input_tokens INTEGER NOT NULL DEFAULT 0,
    total_output_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost_usd REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS steps (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    latency_ms INTEGER,
    input TEXT NOT NULL DEFAULT '{}',
    output TEXT NOT NULL DEFAULT '{}',
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    error TEXT,
    annotation TEXT,
    verdict TEXT
);

CREATE INDEX IF NOT EXISTS idx_steps_session ON steps(session_id, sequence);
CREATE INDEX IF NOT EXISTS idx_sessions_framework ON sessions(framework);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
`;

function defaultDbPath(): string {
  const envPath = process.env.AGENT_REPLAY_DB;
  if (envPath) return envPath;
  const dir = path.join(os.homedir(), '.agent-replay');
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, 'replay.db');
}

export class Store {
  private db: Database.Database;

  constructor(dbPath?: string) {
    this.db = new Database(dbPath || defaultDbPath());
    this.db.pragma('journal_mode = WAL');
    this.db.pragma('foreign_keys = ON');
    this.db.exec(SCHEMA_SQL);
  }

  saveSession(session: Session): void {
    this.db.prepare(`
      INSERT OR REPLACE INTO sessions
      (id, name, framework, model, started_at, ended_at, status, tags, metadata,
       total_input_tokens, total_output_tokens, total_cost_usd)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      session.id,
      session.name || null,
      session.framework,
      session.model,
      session.startedAt.toISOString(),
      session.endedAt?.toISOString() || null,
      session.status,
      JSON.stringify(session.tags),
      JSON.stringify(session.metadata),
      session.totalInputTokens,
      session.totalOutputTokens,
      session.totalCostUsd,
    );
  }

  saveStep(step: Step): void {
    this.db.prepare(`
      INSERT OR REPLACE INTO steps
      (id, session_id, sequence, type, started_at, ended_at, latency_ms,
       input, output, input_tokens, output_tokens, cost_usd, error, annotation, verdict)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      step.id,
      step.sessionId,
      step.sequence,
      step.type,
      step.startedAt.toISOString(),
      step.endedAt?.toISOString() || null,
      step.latencyMs || null,
      JSON.stringify(step.input),
      JSON.stringify(step.output),
      step.inputTokens,
      step.outputTokens,
      step.costUsd,
      step.error || null,
      step.annotation || null,
      step.verdict || null,
    );
  }

  getSession(sessionId: string, includeSteps = true): Session | undefined {
    const row = this.db.prepare('SELECT * FROM sessions WHERE id = ?').get(sessionId) as any;
    if (!row) return undefined;
    const session = this.rowToSession(row);
    if (includeSteps) {
      session.steps = this.getSteps(sessionId);
    }
    return session;
  }

  listSessions(limit = 20, framework?: string, tag?: string): Session[] {
    let query = 'SELECT * FROM sessions WHERE 1=1';
    const params: any[] = [];

    if (framework) {
      query += ' AND framework = ?';
      params.push(framework);
    }
    if (tag) {
      query += ' AND tags LIKE ?';
      params.push(`%"${tag}"%`);
    }
    query += ' ORDER BY started_at DESC LIMIT ?';
    params.push(limit);

    const rows = this.db.prepare(query).all(...params) as any[];
    return rows.map(r => this.rowToSession(r));
  }

  getSteps(sessionId: string): Step[] {
    const rows = this.db.prepare(
      'SELECT * FROM steps WHERE session_id = ? ORDER BY sequence'
    ).all(sessionId) as any[];
    return rows.map(r => this.rowToStep(r));
  }

  close(): void {
    this.db.close();
  }

  private rowToSession(row: any): Session {
    return {
      id: row.id,
      name: row.name || undefined,
      framework: row.framework,
      model: row.model,
      startedAt: new Date(row.started_at),
      endedAt: row.ended_at ? new Date(row.ended_at) : undefined,
      status: row.status,
      tags: JSON.parse(row.tags || '[]'),
      metadata: JSON.parse(row.metadata || '{}'),
      totalInputTokens: row.total_input_tokens,
      totalOutputTokens: row.total_output_tokens,
      totalCostUsd: row.total_cost_usd,
      steps: [],
    };
  }

  private rowToStep(row: any): Step {
    return {
      id: row.id,
      sessionId: row.session_id,
      sequence: row.sequence,
      type: row.type,
      startedAt: new Date(row.started_at),
      endedAt: row.ended_at ? new Date(row.ended_at) : undefined,
      latencyMs: row.latency_ms || undefined,
      input: JSON.parse(row.input || '{}'),
      output: JSON.parse(row.output || '{}'),
      inputTokens: row.input_tokens,
      outputTokens: row.output_tokens,
      costUsd: row.cost_usd,
      error: row.error || undefined,
      annotation: row.annotation || undefined,
      verdict: row.verdict || undefined,
    };
  }
}
