"""Export engine for agent-replay.

Supports JSONL (one JSON object per step) and HTML (self-contained report).
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from io import StringIO
from typing import TextIO

from agent_replay.session import Session


def export_jsonl(session: Session, out: TextIO | None = None) -> str:
    """Export a session as JSONL — one JSON line per step.

    Args:
        session: The session to export.
        out: Optional file-like object to write to. If None, returns the string.

    Returns:
        The JSONL string if no output file is provided.
    """
    buf = out or StringIO()

    # Write session header as first line
    session_dict = {
        "type": "session",
        "id": session.id,
        "name": session.name,
        "framework": session.framework,
        "model": session.model,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "status": session.status,
        "tags": session.tags,
        "metadata": session.metadata,
        "total_input_tokens": session.total_input_tokens,
        "total_output_tokens": session.total_output_tokens,
        "total_cost_usd": session.total_cost_usd,
    }
    buf.write(json.dumps(session_dict, default=str) + "\n")

    # Write each step
    for step in session.steps:
        step_dict = {
            "type": "step",
            "id": step.id,
            "session_id": step.session_id,
            "sequence": step.sequence,
            "step_type": step.type,
            "started_at": step.started_at.isoformat(),
            "ended_at": step.ended_at.isoformat() if step.ended_at else None,
            "latency_ms": step.latency_ms,
            "input": step.input,
            "output": step.output,
            "input_tokens": step.input_tokens,
            "output_tokens": step.output_tokens,
            "cost_usd": step.cost_usd,
            "error": step.error,
            "annotation": step.annotation,
            "verdict": step.verdict,
        }
        buf.write(json.dumps(step_dict, default=str) + "\n")

    if out is None:
        assert isinstance(buf, StringIO)
        return buf.getvalue()
    return ""


def export_html(session: Session, out: TextIO | None = None) -> str:
    """Export a session as a self-contained HTML report.

    Args:
        session: The session to export.
        out: Optional file-like object to write to. If None, returns the string.

    Returns:
        The HTML string if no output file is provided.
    """
    buf = out or StringIO()

    cost_str = f"${session.total_cost_usd:.4f}"
    total_tokens = session.total_input_tokens + session.total_output_tokens
    ended = session.ended_at.isoformat() if session.ended_at else "—"

    steps_html = ""
    for step in session.steps:
        input_json = html.escape(json.dumps(step.input, indent=2, default=str))
        output_json = html.escape(json.dumps(step.output, indent=2, default=str))
        error_html = (
            f'<div class="error">Error: {html.escape(step.error)}</div>' if step.error else ""
        )
        annotation_html = (
            f'<div class="annotation">📝 {html.escape(step.annotation)}</div>'
            if step.annotation
            else ""
        )
        verdict_html = ""
        if step.verdict:
            cls = "pass" if step.verdict == "pass" else "fail"
            verdict_html = f'<span class="verdict {cls}">{step.verdict.upper()}</span>'

        steps_html += f"""
        <div class="step">
            <div class="step-header">
                <span class="step-seq">#{step.sequence}</span>
                <span class="step-type">{html.escape(step.type)}</span>
                {verdict_html}
                <span class="step-tokens">{step.input_tokens} in / {step.output_tokens} out</span>
                <span class="step-cost">${step.cost_usd:.4f}</span>
                <span class="step-latency">{step.latency_ms or 0}ms</span>
            </div>
            {error_html}
            {annotation_html}
            <details>
                <summary>Input</summary>
                <pre><code>{input_json}</code></pre>
            </details>
            <details>
                <summary>Output</summary>
                <pre><code>{output_json}</code></pre>
            </details>
        </div>
        """

    report = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>agent-replay report — {html.escape(session.name or session.id)}</title>
    <style>
        :root {{
            --bg: #0d1117;
            --surface: #161b22;
            --border: #30363d;
            --text: #e6edf3;
            --text-dim: #8b949e;
            --accent: #58a6ff;
            --green: #3fb950;
            --red: #f85149;
            --orange: #d29922;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont,
                'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        h1 {{
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            color: var(--accent);
        }}
        .meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0 2rem;
        }}
        .meta-item {{ }}
        .meta-label {{ color: var(--text-dim); font-size: 0.8rem; text-transform: uppercase; }}
        .meta-value {{ font-weight: 600; }}
        .step {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .step-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
            margin-bottom: 0.5rem;
        }}
        .step-seq {{
            font-weight: 700;
            color: var(--accent);
        }}
        .step-type {{
            background: var(--border);
            padding: 0.1rem 0.5rem;
            border-radius: 4px;
            font-size: 0.85rem;
        }}
        .step-tokens, .step-cost, .step-latency {{
            color: var(--text-dim);
            font-size: 0.85rem;
        }}
        .verdict {{
            padding: 0.1rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
        }}
        .verdict.pass {{ background: var(--green); color: #000; }}
        .verdict.fail {{ background: var(--red); color: #fff; }}
        .error {{
            background: #f8514922;
            border-left: 3px solid var(--red);
            padding: 0.5rem;
            margin: 0.5rem 0;
            border-radius: 4px;
            font-size: 0.9rem;
        }}
        .annotation {{
            background: #d2992222;
            border-left: 3px solid var(--orange);
            padding: 0.5rem;
            margin: 0.5rem 0;
            border-radius: 4px;
            font-size: 0.9rem;
        }}
        details {{
            margin-top: 0.5rem;
        }}
        summary {{
            cursor: pointer;
            color: var(--accent);
            font-size: 0.9rem;
            user-select: none;
        }}
        pre {{
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.75rem;
            overflow-x: auto;
            font-size: 0.8rem;
            margin-top: 0.25rem;
        }}
        code {{ color: var(--text); }}
        .footer {{
            text-align: center;
            color: var(--text-dim);
            font-size: 0.8rem;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔁 {html.escape(session.name or session.id)}</h1>
        <div class="meta">
            <div class="meta-item">
                <div class="meta-label">Session ID</div>
                <div class="meta-value">{html.escape(session.id)}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Framework</div>
                <div class="meta-value">{html.escape(session.framework)}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Model</div>
                <div class="meta-value">{html.escape(session.model)}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Status</div>
                <div class="meta-value">{html.escape(session.status)}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Started</div>
                <div class="meta-value">{html.escape(session.started_at.isoformat())}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Ended</div>
                <div class="meta-value">{html.escape(ended)}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Total Tokens</div>
                <div class="meta-value">{total_tokens:,}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Total Cost</div>
                <div class="meta-value">{cost_str}</div>
            </div>
        </div>

        <h2 style="margin-bottom: 1rem;">Steps ({len(session.steps)})</h2>
        {steps_html}

        <div class="footer">
            Generated by agent-replay · {datetime.now().isoformat()}
        </div>
    </div>
</body>
</html>"""

    buf.write(report)

    if out is None:
        assert isinstance(buf, StringIO)
        return buf.getvalue()
    return ""
