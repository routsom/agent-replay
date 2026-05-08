"""agent-replay record — Record subcommand (placeholder for pipe-based recording)."""

from __future__ import annotations

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def record_command(
    name: str | None = typer.Option(None, "--name", "-n", help="Session name"),
    framework: str = typer.Option("custom", "--framework", "-f", help="Framework name"),
    model: str = typer.Option("unknown", "--model", "-m", help="Model name"),
    db: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Start a recording session (reads JSON steps from stdin)."""
    import json
    import sys

    from agent_replay.recorder import Recorder

    typer.echo("📹 Recording session. Send JSON step objects to stdin, one per line.")
    typer.echo("   Send EOF (Ctrl+D) to end the session.")
    typer.echo()

    with Recorder(name=name, framework=framework, model=model, db_path=db) as recorder:
        typer.echo(f"Session ID: {recorder.session.id}")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                step = recorder.step(
                    step_type=data.get("type", "message"),
                    input=data.get("input", {}),
                )
                step.finish(
                    output=data.get("output", {}),
                    input_tokens=data.get("input_tokens", 0),
                    output_tokens=data.get("output_tokens", 0),
                    error=data.get("error"),
                )
            except json.JSONDecodeError:
                typer.echo(f"⚠️  Skipping invalid JSON: {line[:80]}", err=True)

    typer.echo(f"\n✅ Session {recorder.session.id} saved ({recorder._sequence_counter} steps)")
